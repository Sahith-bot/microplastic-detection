"""Pure-numpy YOLOv8 detect forward pass (TEST-ONLY: lets us verify best.pt in a sandbox with no torch).
The real website uses Ultralytics; this only reproduces its outputs for local checking."""
import numpy as np, cv2
import ptload


def P(m, k):
    v = m._parameters.get(k) if hasattr(m, "_parameters") else None
    return None if v is None else np.asarray(v, np.float32)


def fuse(conv_mod):
    c, bn = conv_mod._modules["conv"], conv_mod._modules["bn"]
    w, b = P(c, "weight"), P(c, "bias")
    g, beta = P(bn, "weight"), P(bn, "bias")
    mu, var = np.asarray(bn._buffers["running_mean"], np.float32), np.asarray(bn._buffers["running_var"], np.float32)
    s = g / np.sqrt(var + bn.eps)
    w = w * s[:, None, None, None]
    b = beta + ((b if b is not None else 0) - mu) * s
    return w, b, c.stride[0], c.padding[0]


def conv2d(x, w, b, s, p):
    C, H, W = x.shape
    O, _, k, _ = w.shape
    if p: x = np.pad(x, ((0, 0), (p, p), (p, p)))
    Ho, Wo = (H + 2 * p - k) // s + 1, (W + 2 * p - k) // s + 1
    if k == 1:
        cols = x[:, ::s, ::s][:, :Ho, :Wo].reshape(C, -1)
        return (w.reshape(O, C) @ cols + b[:, None]).reshape(O, Ho, Wo)
    sv = np.lib.stride_tricks.sliding_window_view(x, (k, k), axis=(1, 2))[:, ::s, ::s][:, :Ho, :Wo]  # C,Ho,Wo,k,k
    cols = sv.transpose(0, 3, 4, 1, 2).reshape(C * k * k, Ho * Wo)
    return (w.reshape(O, -1) @ cols + b[:, None]).reshape(O, Ho, Wo)


silu = lambda x: x / (1 + np.exp(-np.clip(x, -60, 60)))


class Net:
    def __init__(self, path):
        ck = ptload.load(path)
        self.m = ck.get("ema") or ck["model"]
        self.names = self.m.names
        self.cache = {}

    def conv(self, mod, x):
        key = id(mod)
        if key not in self.cache: self.cache[key] = fuse(mod)
        return silu(conv2d(x, *self.cache[key]))

    def run(self, mod, x):
        t = type(mod).__name__
        M = mod._modules
        if t == "Conv": return self.conv(mod, x)
        if t == "C2f":
            y = self.conv(M["cv1"], x)
            ys = list(np.split(y, 2, 0))
            for bm in M["m"]._modules.values():
                h = self.conv(bm._modules["cv2"], self.conv(bm._modules["cv1"], ys[-1]))
                ys.append(ys[-1] + h if bm.add else h)
            return self.conv(M["cv2"], np.concatenate(ys, 0))
        if t == "SPPF":
            y = [self.conv(M["cv1"], x)]
            for _ in range(3):
                z = np.pad(y[-1], ((0, 0), (2, 2), (2, 2)), constant_values=-np.inf)
                y.append(np.lib.stride_tricks.sliding_window_view(z, (5, 5), axis=(1, 2)).max((3, 4)))
            return self.conv(M["cv2"], np.concatenate(y, 0))
        if t == "Upsample": return x.repeat(2, 1).repeat(2, 2)
        raise ValueError(t)

    def head(self, det, feats):
        outs, anchors, strides = [], [], []
        for i, f in enumerate(feats):
            br = []
            for seq in (det._modules["cv2"]._modules[str(i)], det._modules["cv3"]._modules[str(i)]):
                s = seq._modules
                h = self.conv(s["1"], self.conv(s["0"], f))
                br.append(conv2d(h, P(s["2"], "weight"), P(s["2"], "bias"), 1, 0))
            o = np.concatenate(br, 0)  # 64+nc, H, W
            C, H, W = o.shape
            outs.append(o.reshape(C, -1))
            sy, sx = np.meshgrid(np.arange(H) + 0.5, np.arange(W) + 0.5, indexing="ij")
            anchors.append(np.stack([sx.ravel(), sy.ravel()], 0))
            strides.append(np.full(H * W, self.stride_list[i]))
        o = np.concatenate(outs, 1); A = np.concatenate(anchors, 1); S = np.concatenate(strides)
        box, cls = o[:64], o[64:]
        d = box.reshape(4, 16, -1)
        d = np.exp(d - d.max(1, keepdims=True)); d /= d.sum(1, keepdims=True)
        d = (d * np.arange(16)[None, :, None]).sum(1)  # 4,N  (l,t,r,b)
        x1y1, x2y2 = A - d[:2], A + d[2:]
        xyxy = np.concatenate([x1y1, x2y2], 0) * S
        return xyxy.T, 1 / (1 + np.exp(-cls.T))

    def forward(self, img640):
        x = img640.transpose(2, 0, 1).astype(np.float32) / 255.0
        mods = self.m._modules["model"]._modules
        ys = []
        for k, mod in mods.items():
            f = mod.f
            if type(mod).__name__ == "Concat":
                x = np.concatenate([ys[j] if j != -1 else x for j in f], 0)
            elif type(mod).__name__ == "Detect":
                H = img640.shape[0]
                self.stride_list = [H // ys[j].shape[1] for j in f]
                return self.head(mod, [ys[j] for j in f])
            else:
                x = self.run(mod, x)
            ys.append(x)


def letterbox(im, size=640):
    h, w = im.shape[:2]
    r = min(size / h, size / w)
    nh, nw = round(h * r), round(w * r)
    im2 = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
    top, left = (size - nh) // 2, (size - nw) // 2
    out = np.full((size, size, 3), 114, np.uint8)
    out[top:top + nh, left:left + nw] = im2
    return out, r, left, top


def predict(net, bgr, conf=0.25, iou=0.7):
    lb, r, dx, dy = letterbox(bgr)
    boxes, scores = net.forward(cv2.cvtColor(lb, cv2.COLOR_BGR2RGB))
    cls = scores.argmax(1); sc = scores.max(1)
    keep = sc > conf
    boxes, cls, sc = boxes[keep], cls[keep], sc[keep]
    out = []
    if len(sc):
        # class-aware NMS
        off = boxes + cls[:, None] * 4096
        idx = cv2.dnn.NMSBoxes([[float(b[0]), float(b[1]), float(b[2] - b[0]), float(b[3] - b[1])] for b in off],
                               sc.tolist(), conf, iou)
        for i in np.array(idx).ravel():
            b = boxes[i].copy(); b[[0, 2]] -= dx; b[[1, 3]] -= dy; b /= r
            out.append((b.tolist(), int(cls[i]), float(sc[i])))
    return out

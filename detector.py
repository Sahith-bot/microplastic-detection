"""YOLOv8 microplastic detector. Uses Ultralytics when available, otherwise a built-in numpy engine
that reads the same best.pt without torch (handy on small free cloud servers)."""
import threading
import cv2
import numpy as np
import config


def _hex_to_bgr(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


class Detector:
    def __init__(self, model_path=config.MODEL_PATH, engine=config.ENGINE):
        self.lock = threading.Lock()
        self.engine = None
        if engine in ("auto", "ultralytics"):
            try:
                from ultralytics import YOLO
                self.model = YOLO(model_path)
                self.names = {int(k): v for k, v in self.model.names.items()}
                self.engine = "ultralytics"
            except ImportError:
                if engine == "ultralytics":
                    raise
        if self.engine is None:
            from engine import npyolo
            self.model = npyolo.Net(model_path)
            self.names = {int(k): v for k, v in self.model.names.items()}
            self.engine = "numpy"
        print(f"[detector] engine={self.engine} classes={self.names}")

    def predict(self, bgr, conf=config.DEFAULT_CONFIDENCE):
        """Returns a list of dicts: {cls, label, name, conf, box:[x1,y1,x2,y2]} in original image pixels."""
        with self.lock:
            if self.engine == "ultralytics":
                r = self.model.predict(bgr, conf=conf, iou=config.IOU_THRESHOLD, imgsz=config.IMG_SIZE, verbose=False)[0]
                raw = [(b.tolist(), int(c), float(s)) for b, c, s in
                       zip(r.boxes.xyxy.cpu().numpy(), r.boxes.cls.cpu().numpy(), r.boxes.conf.cpu().numpy())]
            else:
                from engine import npyolo
                raw = npyolo.predict(self.model, bgr, conf=conf, iou=config.IOU_THRESHOLD)
        h, w = bgr.shape[:2]
        dets = []
        for box, c, s in sorted(raw, key=lambda t: -t[2]):
            x1, y1, x2, y2 = [float(v) for v in box]
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
            label = self.names[c]
            dets.append({"cls": c, "label": label, "name": config.DISPLAY_NAMES.get(label, label.title()),
                         "conf": round(s, 4), "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                         "width_px": round(x2 - x1, 1), "height_px": round(y2 - y1, 1)})
        for i, d in enumerate(dets, 1):
            d["id"] = i
        return dets

    @staticmethod
    def annotate(bgr, dets):
        out = bgr.copy()
        h, w = out.shape[:2]
        t = max(1, round(min(h, w) / 400))
        fs = max(0.4, min(h, w) / 1100)
        for d in dets:
            x1, y1, x2, y2 = map(int, d["box"])
            col = _hex_to_bgr(config.CLASS_COLORS.get(d["label"], "#00a0a0"))
            cv2.rectangle(out, (x1, y1), (x2, y2), col, t + 1)
            txt = f'{d["id"]} {d["name"]} {d["conf"]:.2f}'
            (tw, th), bl = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, fs, t)
            ty = y1 - 4 if y1 - th - 6 > 0 else y1 + th + 6
            lx = max(0, min(x1, w - tw - 6))  # keep the label inside the image
            cv2.rectangle(out, (lx, ty - th - 4), (lx + tw + 6, ty + 3), col, -1)
            cv2.putText(out, txt, (lx + 3, ty), cv2.FONT_HERSHEY_SIMPLEX, fs, (255, 255, 255), t, cv2.LINE_AA)
        return out


def level_for(value, levels):
    for lv in levels:
        if lv["max"] is None or value <= lv["max"]:
            return lv
    return levels[-1]


def summarize(dets, names, volume_l=None):
    counts = {lbl: 0 for lbl in names.values()}
    conf_sum = {lbl: 0.0 for lbl in names.values()}
    for d in dets:
        counts[d["label"]] += 1
        conf_sum[d["label"]] += d["conf"]
    total = len(dets)
    per_class = []
    for lbl, n in counts.items():
        per_class.append({"label": lbl, "name": config.DISPLAY_NAMES.get(lbl, lbl.title()), "count": n,
                          "percent": round(100 * n / total, 1) if total else 0.0,
                          "avg_conf": round(conf_sum[lbl] / n, 3) if n else None,
                          "color": config.CLASS_COLORS.get(lbl, "#00a0a0")})
    lv = level_for(total, config.CONTAMINATION_LEVELS)
    dominant = max(per_class, key=lambda p: p["count"]) if total else None
    s = {"total": total, "per_class": per_class,
         "level": lv["level"], "level_color": lv["color"], "level_meaning": lv["meaning"],
         "dominant": dominant["name"] if dominant else None,
         "mean_conf": round(sum(d["conf"] for d in dets) / total, 3) if total else None,
         "thresholds": [{"level": l["level"], "max": l["max"], "color": l["color"]} for l in config.CONTAMINATION_LEVELS]}
    if volume_l:
        conc = total / volume_l
        s["volume_l"] = volume_l
        s["per_litre"] = round(conc, 2)
        s["conc_level"] = level_for(conc, config.CONCENTRATION_LEVELS_PER_L)["level"]
    return s

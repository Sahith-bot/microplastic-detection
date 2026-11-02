"""Load an Ultralytics .pt checkpoint WITHOUT torch (test-only helper).
Maps torch storages to numpy arrays and every module class to a generic object."""
import pickle, zipfile, numpy as np, collections

DT = {"FloatStorage": np.float32, "HalfStorage": np.float16, "DoubleStorage": np.float64,
      "LongStorage": np.int64, "IntStorage": np.int32, "BoolStorage": np.bool_, "ByteStorage": np.uint8}


class Obj:
    def __init__(self, *a, **k): pass
    def __setstate__(self, s):
        if isinstance(s, dict): self.__dict__.update(s)
        elif isinstance(s, tuple) and len(s) == 2 and isinstance(s[1], dict): self.__dict__.update(s[1] or {}); self.__dict__.update(s[0] or {})
    def __call__(self, *a, **k): return self


def _make(name):
    return type(name, (Obj,), {})


def load(path):
    z = zipfile.ZipFile(path)
    root = z.namelist()[0].split("/")[0]

    def rebuild_tensor(storage, offset, size, stride, *rest):
        if len(size) == 0:
            return storage[offset]
        return np.lib.stride_tricks.as_strided(storage[offset:], shape=size,
                                               strides=[s * storage.itemsize for s in stride]).copy()

    def rebuild_param(data, *a):
        return data

    class U(pickle.Unpickler):
        def find_class(self, mod, name):
            if name == "_rebuild_tensor_v2": return rebuild_tensor
            if name == "_rebuild_parameter": return rebuild_param
            if mod == "collections" and name == "OrderedDict": return collections.OrderedDict
            if mod.startswith("torch") and name in DT: return name
            if mod == "torch" and name in ("float16", "float32"): return name
            if mod in ("builtins", "copyreg", "_codecs") or mod == "collections":
                return super().find_class(mod, name)
            return _make(name)

        def persistent_load(self, pid):
            _, stype, key, loc, n = pid
            if not isinstance(stype, str): stype = type(stype).__name__
            buf = z.read(f"{root}/data/{key}")
            return np.frombuffer(buf, dtype=DT.get(stype, np.float32))

    return U(z.open(f"{root}/data.pkl")).load()

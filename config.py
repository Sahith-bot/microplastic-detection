"""All tunable settings in one place. Edit these values (or set environment variables) to match your paper."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.environ.get("MODEL_PATH", os.path.join(BASE_DIR, "models", "best.pt"))

# "auto" -> use Ultralytics if it is installed, otherwise the built-in lightweight numpy engine.
# "ultralytics" or "numpy" to force one.
ENGINE = os.environ.get("ENGINE", "auto")

IMG_SIZE = 640                 # same imgsz the model was trained with
DEFAULT_CONFIDENCE = 0.25      # detections below this confidence are discarded (user can change it in the UI)
IOU_THRESHOLD = 0.7            # NMS overlap threshold (Ultralytics default)
MAX_UPLOAD_MB = 15             # Vercel itself caps requests at 4.5 MB; the browser shrinks big images before upload
MAX_RETURN_SIDE = 1280         # longest side (px) of the annotated image sent back to the browser
ALLOWED_EXT = {"jpg", "jpeg", "png", "bmp", "webp", "tif", "tiff"}

# The model's class "pallet" is the microplastic shape usually called "pellet".
DISPLAY_NAMES = {"fiber": "Fiber", "film": "Film", "fragment": "Fragment", "pallet": "Pellet"}

# ---------- Contamination thresholds (particles detected per image) ----------
# Level is chosen by the TOTAL count of detected particles in the image.
# Upper bounds are inclusive. Replace with the values from your study.
CONTAMINATION_LEVELS = [
    {"level": "Low",       "max": 5,    "color": "#2e9e6b",
     "meaning": "Few microplastic particles detected. The sample shows light contamination."},
    {"level": "Moderate",  "max": 15,   "color": "#e0a526",
     "meaning": "A noticeable number of particles detected. Further sampling and source checks are advisable."},
    {"level": "High",      "max": None, "color": "#d1495b",
     "meaning": "Many particles detected. The sample indicates heavy microplastic contamination."},
]

# Optional: if the user enters the filtered sample volume (litres), the report also gives particles per litre.
# Levels for particles/L (inclusive upper bounds). Used only when a volume is given.
CONCENTRATION_LEVELS_PER_L = [
    {"level": "Low", "max": 10}, {"level": "Moderate", "max": 100}, {"level": "High", "max": None},
]

# Colours used for boxes / charts (BGR for OpenCV is derived automatically).
CLASS_COLORS = {"fiber": "#1f77b4", "film": "#17becf", "fragment": "#2ca02c", "pallet": "#9467bd"}

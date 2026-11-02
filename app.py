"""MicroPlastic Detector - Flask web app (YOLOv8 + PDF report).
Stateless: nothing is saved on the server, so it runs on Vercel (serverless), Docker, EC2, Render, etc.
Run locally:  python app.py   then open http://localhost:7860"""
import base64
import io
import os
import re
import uuid
from datetime import datetime, timezone

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

import config
import knowledge
from detector import Detector, summarize
from report_pdf import build_pdf

# All files sit in one folder (flat layout). Only these front-end files are served to the browser.
app = Flask(__name__, template_folder=config.BASE_DIR, static_folder=None)
ASSETS = {"style.css": "text/css", "common.js": "text/javascript", "app.js": "text/javascript",
          "report.js": "text/javascript"}
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
detector = Detector()


def _jpeg_data_url(bgr, max_side=config.MAX_RETURN_SIDE, quality=88):
    h, w = bgr.shape[:2]
    s = max_side / max(h, w)
    if s < 1:
        bgr = cv2.resize(bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


@app.get("/static/<name>")
def asset(name):
    if name not in ASSETS:
        return "Not found", 404
    return send_from_directory(config.BASE_DIR, name, mimetype=ASSETS[name], max_age=3600)


@app.get("/")
def index():
    return render_template("index.html", default_conf=config.DEFAULT_CONFIDENCE, page="detect")


@app.get("/report")
def report_page():
    return render_template("report.html", page="report")


@app.get("/api/info")
def api_info():
    return jsonify({"classes": detector.names, "display_names": config.DISPLAY_NAMES, "info": knowledge.INFO,
                    "general": knowledge.GENERAL, "colors": config.CLASS_COLORS, "engine": detector.engine,
                    "thresholds": config.CONTAMINATION_LEVELS, "default_conf": config.DEFAULT_CONFIDENCE})


@app.post("/api/detect")
def api_detect():
    f = request.files.get("image")
    if not f or not f.filename:
        return jsonify({"error": "Please choose an image file."}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in config.ALLOWED_EXT:
        return jsonify({"error": f"Unsupported file type '.{ext}'. Use JPG, PNG, BMP, WEBP or TIFF."}), 400
    img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "The file could not be read as an image."}), 400
    try:
        conf = float(request.form.get("conf", config.DEFAULT_CONFIDENCE))
    except ValueError:
        conf = config.DEFAULT_CONFIDENCE
    conf = min(max(conf, 0.05), 0.95)
    try:
        volume = float(request.form.get("volume", "").strip() or 0) or None
        if volume is not None and volume <= 0:
            volume = None
    except ValueError:
        volume = None
    sample_name = request.form.get("sample_name", "").strip()[:80]
    filename = request.form.get("original_name", "").strip()[:120] or os.path.basename(f.filename)[:120]

    dets = detector.predict(img, conf=conf)
    annotated = detector.annotate(img, dets)
    h, w = img.shape[:2]
    return jsonify({"id": uuid.uuid4().hex[:12], "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "filename": filename, "sample_name": sample_name, "width": w, "height": h,
                    "conf": conf, "engine": detector.engine, "detections": dets,
                    "summary": summarize(dets, detector.names, volume),
                    "annotated": _jpeg_data_url(annotated)})


@app.post("/api/report")
def api_report():
    """Builds the PDF from a result the browser sends back (the server keeps nothing)."""
    res = request.get_json(silent=True)
    if not res or "summary" not in res or "annotated" not in res:
        return jsonify({"error": "No detection result was sent."}), 400
    m = re.match(r"^data:image/\w+;base64,(.+)$", res["annotated"])
    if not m:
        return jsonify({"error": "Invalid image data."}), 400
    try:
        # rebuild the summary on the server so the report always uses the configured thresholds
        names = detector.names
        dets = [d for d in res.get("detections", []) if d.get("label") in names.values()]
        res["summary"] = summarize(dets, names, res["summary"].get("volume_l"))
        img_bytes = io.BytesIO(base64.b64decode(m.group(1)))
        pdf = build_pdf(res, img_bytes)
    except Exception as ex:  # malformed payload
        return jsonify({"error": f"Could not build the report: {ex}"}), 400
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", res.get("sample_name") or os.path.splitext(res.get("filename", "image"))[0])[:40]
    return send_file(io.BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
                     download_name=f"microplastic_report_{name}.pdf")


@app.errorhandler(413)
def too_big(_):
    return jsonify({"error": f"File is too large (max {config.MAX_UPLOAD_MB} MB)."}), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)), debug=False)

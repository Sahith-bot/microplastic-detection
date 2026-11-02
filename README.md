---
title: MicroPlastic Detector
emoji: 💧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# MicroPlastic Detector

A website that detects microplastics in water-sample images with a YOLOv8 model and produces a PDF report based on contamination thresholds.

(The block above is only for Hugging Face Spaces. GitHub just shows it as a small table.)

## What it does
1. **Detect page (`/`)**: upload an image. You can also add a sample name, the volume of water filtered, and a confidence threshold. The page then shows:
   - the image with every particle boxed and labelled
   - counts by type
   - the contamination level
   - information about each type found
   - a table of all detections
2. **Report page (`/report`)**: the threshold assessment with its Low / Moderate / High scale, the summary, and a **Download PDF** button.

The model detects four classes: **fiber, film, fragment, pallet**. "pallet" is the class name in your dataset; the site shows it as **Pellet**.

## Project structure
```
app.py            Flask server: pages + API (/api/detect, /api/report -> PDF). Stateless: nothing stored on the server
api/index.py      Vercel entry point (just imports app.py)
vercel.json       Vercel settings (Mumbai region, routes everything to the Flask app)
detector.py       Loads best.pt, runs detection, draws boxes, applies thresholds
engine/           Lightweight YOLOv8 engine (numpy + OpenCV, reads best.pt without PyTorch)
report_pdf.py     PDF report (ReportLab)
knowledge.py      Information text for each microplastic type
config.py         ⚙️ All settings: thresholds, default confidence, colours
models/best.pt    Your trained YOLOv8s weights
templates/, static/   Frontend (HTML, CSS, JS)
```

## Change the thresholds
Edit `CONTAMINATION_LEVELS` in `config.py`. It holds the particles-per-image limits. The defaults are Low ≤ 5, Moderate 6–15 and High > 15.

If the user enters a water volume, `CONCENTRATION_LEVELS_PER_L` is also used to grade particles per litre. Replace both with the values from your study.

## Two ways to run the model
- **Built-in engine (default).** It reads `best.pt` directly with numpy and OpenCV and doesn't need PyTorch, so the app uses only about 320 MB of RAM and runs on free cloud plans. It takes about 1 second per image on a CPU.
- **Ultralytics.** Uncomment `ultralytics` in `requirements.txt`. The app switches to it automatically, or you can force it with the environment variable `ENGINE=ultralytics`. It needs about 2 GB of RAM.

Both engines produce the same detections. To swap in a retrained model, replace `models/best.pt`.

## Run locally
```bash
pip install -r requirements.txt
python app.py
# open http://localhost:7860
```

## Put it online (free)

### Option A: Vercel (recommended)
1. Push this folder to a **GitHub repository**. `best.pt` is 21 MB, which is under GitHub's 100 MB limit.
   ```bash
   git init && git add . && git commit -m "MicroPlastic Detector"
   git branch -M main
   git remote add origin https://github.com/<you>/microplastic-detector.git
   git push -u origin main
   ```
2. At vercel.com, choose **Add New → Project** and import the repo.
3. Leave Framework Preset as **Other** and leave the build settings empty, then click **Deploy**.
4. In about 2–3 minutes your site is live at `https://<project>.vercel.app`. Every later `git push` redeploys it automatically.

Notes for Vercel:
- The first request after the site has been idle takes a few extra seconds while the model loads (a "cold start").
- Vercel limits uploads to 4.5 MB. The page shrinks large photos in the browser before uploading, so users don't need to do anything.
- If the build complains about the bundle size, delete `gunicorn` from `requirements.txt`. Vercel doesn't need it.


### Option B: Hugging Face Spaces
1. Create an account at huggingface.co, then go to **New Space**.
2. Set **SDK: Docker** (Blank template) and Visibility: **Public**.
3. Under **Files → Add file → Upload files**, upload *everything in this folder*, keeping the folder structure. That includes `models/best.pt`.
4. The Space builds by itself. Your site goes live at `https://huggingface.co/spaces/<username>/<space-name>`.

### Option C: Render
1. Push this folder to a GitHub repository. `best.pt` is 21 MB, which is under GitHub's 100 MB limit.
2. At render.com, choose **New → Web Service** and connect the repo.
3. Set **Runtime: Docker** and **Instance: Free**, then deploy.
4. Your site goes live at `https://<name>.onrender.com`. Free instances sleep when idle, so the first visit after a break takes about 30–60 seconds.

### Option D: Any VM (AWS EC2 / GCP / Azure)
```bash
docker build -t microplastic .
docker run -d -p 80:7860 microplastic
```

## Notes
- Nothing is stored on the server. The latest result is kept in the user's browser so the Report page and PDF can use it.
- The results are an automated screening estimate. Confirm them with FTIR or Raman spectroscopy where accuracy matters.

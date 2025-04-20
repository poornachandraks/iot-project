import os
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import matplotlib.pyplot as plt

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import firebase_admin
from firebase_admin import credentials, db
from config import dbURL

# ------------------ Firebase Setup ------------------

if not firebase_admin._apps:
    cred = credentials.Certificate("key.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': dbURL
    })


# ------------------ FastAPI Setup ------------------
app = FastAPI()

UPLOAD_FOLDER = "static/uploads"
PROCESSED_FOLDER = "static/processed"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

whole, broken, id = None, None, 0

# ------------------ Routes ------------------

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    uploaded_files = sorted(Path(UPLOAD_FOLDER).glob("*"), reverse=True)
    processed_files = sorted(Path(PROCESSED_FOLDER).glob("*"), reverse=True)
    global whole, broken
    latest_upload = uploaded_files[0].name if uploaded_files else None
    latest_processed = processed_files[0].name if processed_files else None

    return templates.TemplateResponse("index.html", {
        "request": request,
        "latest_file": latest_upload,
        "processed_file": latest_processed,
        "whole_grains": whole,
        "broken_grains": broken
    })


@app.get("/local", response_class=HTMLResponse)
async def form_get(request: Request):
    uploaded_files = sorted(Path(UPLOAD_FOLDER).glob("*"), reverse=True)
    processed_files = sorted(Path(PROCESSED_FOLDER).glob("*"), reverse=True)
    global whole, broken
    latest_upload = uploaded_files[0].name if uploaded_files else None
    latest_processed = processed_files[0].name if processed_files else None

    return templates.TemplateResponse("index_2.html", {
        "request": request,
        "latest_file": latest_upload,
        "processed_file": latest_processed,
        "whole_grains": whole,
        "broken_grains": broken
    })


@app.post("/", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    global whole, broken, id
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Process the image after upload
    whole, broken = process_image(file_path, os.path.join(PROCESSED_FOLDER, filename))
    
    # Send data to Firebase Realtime Database
    ref = db.reference("/grain_analysis")
    ref.push({
        "id": id,
        "timestamp": datetime.now().isoformat(),
        "whole_grains": whole,
        "broken_grains": broken
        })
    id=id+1

    return RedirectResponse(url="/", status_code=303)


# ------------------ Image Processing Function ------------------

def process_image(input_path, output_path):
    image = cv2.imread(input_path)
    original = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

    sure_bg = cv2.dilate(opening, kernel, iterations=3)
    dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist_transform, 0.5 * dist_transform.max(), 255, 0)

    sure_fg = np.uint8(sure_fg)
    unknown = cv2.subtract(sure_bg, sure_fg)

    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    cv2.watershed(original, markers)
    watershed_img = original.copy()
    watershed_img[markers == -1] = [0, 0, 255]

    contours, _ = cv2.findContours((markers > 1).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    areas = [cv2.contourArea(c) for c in contours if cv2.contourArea(c) > 50]
    average_area = np.mean(areas) if areas else 0
    min_broken_area = int(0.5 * average_area)
    min_whole_area = int(0.8 * average_area)

    whole_grains = 0
    broken_grains = 0
    classified_img = original.copy()

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_whole_area:
            whole_grains += 1
            color = (0, 255, 0)
        elif area > min_broken_area:
            broken_grains += 1
            color = (0, 0, 255)
        else:
            continue
        cv2.drawContours(classified_img, [contour], -1, color, 2)

        cv2.putText(classified_img, f'Whole: {whole_grains}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)
        cv2.putText(classified_img, f'Broken: {broken_grains}', (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)


    cv2.imwrite(output_path, classified_img)

    return whole_grains, broken_grains
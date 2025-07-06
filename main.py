# main.py (FastAPI with database integration + list capture support + dual-camera ready)
from fastapi import FastAPI, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
import uuid
import os
import cv2
import threading
import time
import shutil

# Database setup
DATABASE_URL = "sqlite:///./captures.db"
en = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=en)
Base = declarative_base()

class Capture(Base):
    __tablename__ = "captures"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    camera_id = Column(Integer)
    filename = Column(String)
    file_type = Column(String)  # image or video
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=en)

# FastAPI app setup
app = FastAPI()
app.mount("/captures", StaticFiles(directory="captures"), name="captures")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Detect connected cameras
@app.get("/cameras")
def list_cameras():
    cams = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.read()[0]:
            cams.append(i)
        cap.release()
    return {"available_cameras": cams}

@app.get("/capture")
def capture_image(camera_index: int = Query(..., ge=0), user_id: str = Query(...), db: Session = Depends(get_db)):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return JSONResponse(status_code=400, content={"error": "Camera not found"})
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return JSONResponse(status_code=500, content={"error": "Failed to capture image"})

    now = datetime.now()
    date_folder = now.strftime('%Y-%m-%d')
    timestamp = now.strftime('%H-%M-%S')
    folder = f"captures/camera_{camera_index}/{date_folder}"
    os.makedirs(folder, exist_ok=True)
    filename = f"{timestamp}.jpg"
    filepath = os.path.join(folder, filename)

    cv2.putText(frame, now.strftime('%Y-%m-%d %H:%M:%S'), (10, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
    cv2.imwrite(filepath, frame)

    db.add(Capture(user_id=user_id, camera_id=camera_index, filename=filepath, file_type="image"))
    db.commit()

    return {"message": "Image saved", "path": f"camera_{camera_index}/{date_folder}/{filename}"}

@app.get("/record")
def record_video(camera_index: int = Query(...), duration: int = Query(5), user_id: str = Query(...), db: Session = Depends(get_db)):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return JSONResponse(status_code=400, content={"error": "Camera not found"})

    fps = 20
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    now = datetime.now()
    date_folder = now.strftime('%Y-%m-%d')
    timestamp = now.strftime('%H-%M-%S')
    folder = f"captures/camera_{camera_index}/{date_folder}"
    os.makedirs(folder, exist_ok=True)
    filename = f"{timestamp}.mp4"
    filepath = os.path.join(folder, filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

    for _ in range(int(duration * fps)):
        ret, frame = cap.read()
        if not ret:
            break
        cv2.putText(frame, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        out.write(frame)

    cap.release()
    out.release()

    db.add(Capture(user_id=user_id, camera_id=camera_index, filename=filepath, file_type="video"))
    db.commit()

    return {"message": f"Video recorded for {duration} seconds", "path": f"camera_{camera_index}/{date_folder}/{filename}"}

@app.get("/list-captures")
def list_captures(camera_index: int = Query(..., ge=0), user_id: str = Query(...), db: Session = Depends(get_db)):
    base_folder = f"captures/camera_{camera_index}"
    if not os.path.exists(base_folder):
        return JSONResponse(status_code=404, content={"error": "No captures found."})

    results = db.query(Capture).filter_by(user_id=user_id, camera_id=camera_index).all()
    files = []
    for record in results:
        rel_path = os.path.relpath(record.filename, "captures")
        file_type = record.file_type
        files.append({
            "name": os.path.basename(record.filename),
            "type": file_type,
            "timestamp": record.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "path": rel_path.replace("\\", "/")
        })

    files.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"files": files}

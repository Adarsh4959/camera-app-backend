from fastapi import FastAPI, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from datetime import datetime
import os
import cv2
import time

# Database setup
DATABASE_URL = "sqlite:///./captures.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Capture(Base):
    __tablename__ = "captures"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    camera_id = Column(Integer)
    filename = Column(String)
    file_type = Column(String)  # image or video
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

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

def current_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def safe_filename(timestamp: str):
    return timestamp.replace(":", "-").replace(" ", "_")

@app.get("/cameras")
def list_cameras():
    cams = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.read()[0]:
            cams.append(i)
        cap.release()
    return {"available_cameras": cams}

def save_image(cap, folder, timestamp):
    ret, frame = cap.read()
    if not ret:
        return None, None

    filename = f"{safe_filename(timestamp)}.jpg"
    filepath = os.path.join(folder, filename)

    # Overlay timestamp on image
    cv2.putText(frame, timestamp, (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.imwrite(filepath, frame)
    return filename, filepath

def save_video(cap, folder, timestamp, duration):
    fps = 20
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    filename = f"{safe_filename(timestamp)}.mp4"
    filepath = os.path.join(folder, filename)
    out = cv2.VideoWriter(filepath, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    for _ in range(int(fps * duration)):
        ret, frame = cap.read()
        if not ret:
            break
        # Timestamp on video frames
        cv2.putText(frame, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        out.write(frame)

    out.release()
    return filename, filepath

@app.get("/capture")
def capture_single(camera_index: int = Query(...), user_id: str = Query(...), db: Session = Depends(get_db)):
    now = datetime.now()
    date_folder = now.strftime('%Y-%m-%d')
    timestamp = current_timestamp()
    cap = cv2.VideoCapture(camera_index)
    if not cap.read()[0]:
        cap.release()
        return JSONResponse(status_code=400, content={"error": "Camera not found"})
    folder = f"captures/camera_{camera_index}/{date_folder}"
    os.makedirs(folder, exist_ok=True)
    filename, filepath = save_image(cap, folder, timestamp)
    cap.release()
    if filename:
        db.add(Capture(user_id=user_id, camera_id=camera_index, filename=filepath, file_type="image"))
        db.commit()
        return {"message": "Captured from camera", "camera_id": camera_index, "path": filename}
    return JSONResponse(status_code=500, content={"error": "Capture failed"})

@app.get("/capture-all")
def capture_all(user_id: str = Query(...), db: Session = Depends(get_db)):
    date_folder = datetime.now().strftime('%Y-%m-%d')
    timestamp = current_timestamp()
    paths = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if not cap.read()[0]:
            cap.release()
            continue
        folder = f"captures/camera_{i}/{date_folder}"
        os.makedirs(folder, exist_ok=True)
        filename, filepath = save_image(cap, folder, timestamp)
        cap.release()
        if filename:
            db.add(Capture(user_id=user_id, camera_id=i, filename=filepath, file_type="image"))
            paths.append((i, filename))
    db.commit()
    return {"message": "Captured from all cameras", "paths": paths}

@app.get("/record-all")
def record_all(user_id: str = Query(...), duration: int = Query(5), db: Session = Depends(get_db)):
    date_folder = datetime.now().strftime('%Y-%m-%d')
    timestamp = current_timestamp()
    paths = []
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if not cap.read()[0]:
            cap.release()
            continue
        folder = f"captures/camera_{i}/{date_folder}"
        os.makedirs(folder, exist_ok=True)
        filename, filepath = save_video(cap, folder, timestamp, duration)
        cap.release()
        if filename:
            db.add(Capture(user_id=user_id, camera_id=i, filename=filepath, file_type="video"))
            paths.append((i, filename))
    db.commit()
    return {"message": "Videos recorded from all cameras", "paths": paths}

@app.get("/auto-combo")
def auto_combo(user_id: str = Query(...), interval: int = Query(10), total: int = Query(60), db: Session = Depends(get_db)):
    stop_time = time.time() + total
    while time.time() < stop_time:
        timestamp = current_timestamp()
        date_folder = datetime.now().strftime('%Y-%m-%d')
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if not cap.read()[0]:
                cap.release()
                continue
            folder = f"captures/camera_{i}/{date_folder}"
            os.makedirs(folder, exist_ok=True)
            img_name, img_path = save_image(cap, folder, timestamp)
            vid_name, vid_path = save_video(cap, folder, timestamp + '_video', 3)
            cap.release()
            if img_name:
                db.add(Capture(user_id=user_id, camera_id=i, filename=img_path, file_type="image"))
            if vid_name:
                db.add(Capture(user_id=user_id, camera_id=i, filename=vid_path, file_type="video"))
        db.commit()
        time.sleep(interval)
    return {"message": "Auto combo finished"}

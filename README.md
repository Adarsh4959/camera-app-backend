 🎥 Camera Capture & Recording Backend (FastAPI + SQLite)

This is a FastAPI-based backend that allows capturing images and recording videos from multiple cameras (e.g., laptop cam, mobile cam via DroidCam), saving them locally and storing metadata in an SQLite database.

---

## ⚙️ Features

- Detects connected cameras.
- Capture image or record video from any selected camera.
- Stores captured files in `captures/` folder.
- Saves metadata (user ID, camera ID, timestamp, type) in SQLite DB.
- Fetch capture history via API (with thumbnail support).
- Auto-capture support (interval + duration).
- Folder renaming for organization.

---

## 📦 Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/camera-capture-backend.git
cd camera-capture-backend

2. Create a virtual environment and install dependencies

python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn sqlalchemy opencv-python python-multipart

3. Run the FastAPI server

uvicorn main:app --reload

The backend will run at: http://localhost:8000
🗃️ Database Details

    Uses SQLite as default (captures.db).

    Automatically created on first run.

    Table: captures

📄 Table: captures
Column	Type	Description
id	Integer	Primary key
user_id	String	User identifier (from frontend)
camera_id	Integer	Camera index (e.g., 0, 1)
filename	String	Path to saved file
file_type	String	'image' or 'video'
timestamp	DateTime	Date and time of capture
To preview the table:

sqlite3 captures.db

-- Inside the SQLite prompt:
.tables
SELECT * FROM captures;
.quit

📷 Testing with Multiple Cameras

    Your system camera appears as /dev/video0.

    To use your phone as a second camera, install DroidCam or Iriun Webcam on phone and Linux.

    Run uvicorn main:app --reload and visit frontend.

    Use /cameras to list available camera indices (e.g., [0, 1]).

    Select and test both cameras independently.

📁 Captures Directory Structure

Saved files are stored like:

captures/
├── camera_0/
│   └── 2025-07-06/
│       └── 10-23-45.jpg
├── camera_1/
│   └── 2025-07-06/
│       └── 10-25-32.mp4

🧪 API Endpoints (for testing)
Endpoint	Method	Description
/cameras	GET	List available camera indices
/capture	GET	Capture image
/record	GET	Record video
/list-captures	GET	Fetch previous captures

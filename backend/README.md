# WarehouseVision AI — Backend API

FastAPI backend application for **WarehouseVision AI**, providing high-performance asynchronous REST endpoints, MongoDB persistence, and an integrated Computer Vision foundation for real-time warehouse monitoring.

---

## Architecture Overview

The backend uses a **simplified monolithic architecture** designed for clean separation of concerns, high throughput, and portfolio clarity:

```text
backend/
├── app/
│   ├── api/          # HTTP routes & dependency injection
│   ├── core/         # Config, Database client, Security, Exceptions
│   ├── models/       # Database collections & persistent schema mappings
│   ├── schemas/      # Pydantic request/response validation models
│   ├── services/     # Business logic & database operations
│   ├── utils/        # File handlers, validators, and serializers
│   ├── vision/       # Computer vision pipeline, detectors, and trackers
│   ├── workers/      # Asynchronous background job processors
│   └── main.py       # FastAPI application factory & lifespan manager
├── storage/          # Local media directory for uploads & processed outputs
├── tests/            # Pytest test suite
├── run.py            # Local execution entrypoint
├── requirements.txt  # Python dependencies
└── .env.example      # Environment variables template
```

---

## Getting Started

### 1. Prerequisites
* **Python 3.11+** (Python 3.12 supported)
* **MongoDB** (Local instance or Docker container)

### 2. Setup Virtual Environment

In the `backend` directory:

```powershell
python -m venv .venv
```

Activate the environment:

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env`:

```powershell
cp .env.example .env
```

Review the values in `.env`:
* `MONGODB_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
* `JWT_SECRET_KEY`: Signing key for JWT tokens
* `FRONTEND_URL`: React frontend origin for CORS (default: `http://localhost:5173`)

### 5. Start MongoDB (Optional for basic API / testing)

If running Docker:
```powershell
docker run -d --name warehouse-mongo -p 27017:27017 mongo:latest
```

---

## Running the Application

### Option A: Using `run.py`
```powershell
python run.py
```

### Option B: Using `uvicorn` CLI
```powershell
uvicorn app.main:app --reload --port 8000
```

The server will be available at:
* **API Root**: [http://localhost:8000/](http://localhost:8000/)
* **Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Health Check Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Service overview & API documentation link |
| `/api/v1/health` | `GET` | Application health and version |
| `/api/v1/health/database` | `GET` | MongoDB connectivity check (200 OK / 503 Service Unavailable) |

---

## Video Upload & Asynchronous Processing

WarehouseVision AI supports asynchronous video ingestion and frame-by-frame YOLO object detection with visual bounding box annotations.

### Endpoints Overview

| Endpoint | Method | Status | Description |
|---|---|:---:|---|
| `/api/v1/inputs/video` | `POST` | 202 Accepted | Upload video file and queue background processing job |
| `/api/v1/processing/{job_id}` | `GET` | 200 OK | Check current processing status and frame progress |
| `/api/v1/processing/{job_id}/result` | `GET` | 200 OK | Retrieve detection statistics and annotated video URL |
| `/api/v1/processing/{job_id}/video` | `GET` | 200 OK | Securely download or stream the annotated video |
| `/api/v1/processing` | `GET` | 200 OK | Paginated history of authenticated user's jobs |

### Specifications

- **Supported Formats**: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`
- **Max Video Size**: 200 MB (`MAX_VIDEO_SIZE_MB=200`)
- **Default Frame Interval**: 1 (processes every frame, configurable via `VIDEO_FRAME_INTERVAL`)
- **Output Encoding**: OpenCV `mp4v` codec

### Processing Job Lifecycle

```text
[POST /api/v1/inputs/video] ──► (status: queued)
                                     │
                                     ▼
                          (status: processing) ◄── [GET /api/v1/processing/{id}]
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
        (status: completed)                     (status: failed)
                 │                                       │
     [GET /processing/{id}/result]                       ▼
     [GET /processing/{id}/video]             Sanitized error detail
```

### Example Usage

#### 1. Upload Video
```bash
curl -X POST "http://localhost:8000/api/v1/inputs/video" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@warehouse_aisle.mp4"
```

Response (`202 Accepted`):
```json
{
  "job_id": "8f03ec419e7a4b8ebbc21a41e974e6f1",
  "status": "queued",
  "message": "Video uploaded and queued for processing."
}
```

#### 2. Poll Status & Progress
```bash
curl -X GET "http://localhost:8000/api/v1/processing/8f03ec419e7a4b8ebbc21a41e974e6f1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response (`200 OK`):
```json
{
  "job_id": "8f03ec419e7a4b8ebbc21a41e974e6f1",
  "status": "processing",
  "progress": 45,
  "processed_frames": 1350,
  "total_frames": 3000,
  "message": "Processing video."
}
```

#### 3. Fetch Completed Results
```bash
curl -X GET "http://localhost:8000/api/v1/processing/8f03ec419e7a4b8ebbc21a41e974e6f1/result" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response (`200 OK`):
```json
{
  "job_id": "8f03ec419e7a4b8ebbc21a41e974e6f1",
  "status": "completed",
  "processed_video_url": "/api/v1/processing/8f03ec419e7a4b8ebbc21a41e974e6f1/video",
  "total_frames": 3000,
  "processed_frames": 3000,
  "detection_count": 1250,
  "duration_seconds": 30.0,
  "error_message": null
}
```

### Processing Limitations

- **In-Process Workers**: Video jobs are executed using FastAPI `BackgroundTasks` within the server process. While ideal for development and single-instance deployments, high-throughput production clusters should use a distributed worker queue (e.g. Celery / Temporal).
- **Domain Classes**: Standard YOLO weights detect common COCO classes (person, vehicle, chair). Specialized warehouse objects (pallets, hardhats, vests) require custom-trained weights.
- **Audio Tracks**: Video re-encoding strips audio tracks as industrial vision monitoring evaluates only visual feed channels.

---

## Running Automated Tests

Run test suite using `pytest`:

```powershell
pytest
```

With verbose output and per-test timing:
```powershell
pytest -v
```

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
  "tracking": {
    "enabled": true,
    "tracker_type": "bytetrack",
    "unique_track_count": 14,
    "max_active_tracks": 6,
    "tracks_by_class": {
      "person": 10,
      "forklift": 4
    },
    "tracked_detections": 1250,
    "frames_with_tracks": 2800,
    "average_objects_per_frame": 0.42
  },
  "error_message": null
}
```

---

## Multi-Object Tracking (ByteTrack)

WarehouseVision AI extends the core YOLO detection pipeline with **persistent multi-object tracking** across video frames.

### Tracking Pipeline Flow

```text
Video File (.mp4)
       │
       ▼
OpenCV VideoCapture
       │
       ▼
YOLO Detection + ByteTrack  ──►  model.track(tracker="bytetrack.yaml", persist=True)
       │
       ▼
Persistent Track IDs        ──►  TrackedObject (track_id, class_id, bbox, center)
       │
       ▼
Frame Annotation            ──►  "class_name #track_id confidence" (e.g. person #12 0.91)
       │
       ▼
OpenCV VideoWriter          ──►  Annotated MP4 Output
```

### Key Design Highlights

1. **Unified Single-Pass Inference**: The pipeline invokes Ultralytics' `model.track()` directly on each frame. Detection and ByteTrack Kalman-filter association happen together in one pass—eliminating duplicate forward passes and reusing the existing loaded YOLO weights from the model cache.
2. **Strict Job Isolation**: A fresh `ObjectTracker` instance is initialized per video processing job and discarded upon completion. Track IDs are scoped strictly to the processing of a single video file, preventing any ID leakage across jobs.
3. **Database Efficiency**: Per-frame bounding boxes are intentionally **not** stored in MongoDB to prevent unbounded document growth. Instead, lightweight aggregate tracking statistics (`unique_tracked_objects`, `max_concurrent_tracks`, `tracks_by_class`, and per-track lifecycle records) are persisted within the `processing_jobs` collection.
4. **Resilient Fallback**: If tracker initialization fails (e.g. missing tracker configuration or uninitialized weights), the pipeline gracefully falls back to detection-only mode without interrupting video processing.

### Tracker Configuration

Configurable via environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `TRACKER_TYPE` | `bytetrack` | Tracker algorithm: `bytetrack` or `botsort` |
| `TRACKER_CONFIDENCE_THRESHOLD` | `0.25` | Minimum detection confidence threshold for tracking |
| `TRACKER_IOU_THRESHOLD` | `0.5` | IoU threshold for matching detections to existing tracks |
| `TRACKER_MAX_AGE` | `30` | Informational maximum frame buffer before dropping lost tracks |

### ByteTrack Limitations & Considerations

- **Visual Re-Identification**: ByteTrack uses spatial bounding box overlap (IoU) and motion velocity (Kalman filter), not visual re-identification embeddings.
- **Occlusion Recovery**: If an object disappears or remains occluded beyond the tracker's buffer threshold, ByteTrack will assign a **new** track ID when the object reappears.
- **Scope**: Track IDs are persistent only within a single continuous video session and cannot be correlated across different cameras or disjoint video uploads.

---

## PPE Compliance Monitoring

WarehouseVision AI includes a **PPE (Personal Protective Equipment) compliance subsystem** that detects and tracks whether workers are wearing required safety gear.

### How It Works

```text
Video Frame
     │
     ▼
YOLO Detection + ByteTrack Tracking
     │
     ▼
Tracked Persons (with persistent IDs)
     │
     ├──► PPE Detector ──► PPE Items (helmet, vest, etc.)
     │
     ▼
PPE Association ──► Match PPE items to persons via bounding-box geometry
     │
     ▼
Per-Worker Compliance ──► compliant / non_compliant / unknown
     │
     ▼
Temporal Confirmation ──► Suppress transient false positives
     │
     ▼
Safety Events ──► MongoDB persistence (with cooldown deduplication)
```

### Important: Model Requirements

**PPE detection requires a YOLO model that is trained to recognise PPE classes** (e.g. `helmet`, `safety helmet`, `vest`, `safety vest`).

A generic pretrained YOLO model (such as `yolo11n.pt` trained on COCO) **does NOT** contain these classes and therefore **cannot** detect PPE.

When PPE classes are unavailable, the system:
- Clearly reports `available: false` with a descriptive reason.
- Does **not** fabricate detections or re-label non-PPE objects.
- Continues running all other safety features (zones, proximity, collision risk) normally.

### PPE Association Algorithm

1. For each PPE detection, compute the bounding-box centre point.
2. Check which tracked person bounding box contains that centre.
3. If the centre is not inside any person, compute the overlap ratio (intersection / PPE area).
4. Assign the PPE to the person with the highest overlap, if above the configured threshold.
5. Reject ambiguous or unassociated PPE items.

### Temporal Confirmation

PPE detection can fail transiently due to occlusion, blur, or camera angle. A **missing PPE** status is only confirmed after the item is absent for `PPE_MISSING_CONFIRMATION_FRAMES` consecutive processed frames (default: 5). This significantly reduces false-positive violations.

### PPE Configuration

| Variable | Default | Description |
|---|---|---|
| `PPE_ENABLED` | `true` | Master toggle for the PPE subsystem |
| `PPE_MODEL_PATH` | *(empty)* | Path to a dedicated PPE YOLO model. If empty, the main model is used (if it supports PPE classes) |
| `PPE_HELMET_CLASSES` | `helmet,safety helmet` | Model class names that map to the "helmet" category |
| `PPE_VEST_CLASSES` | `vest,safety vest` | Model class names that map to the "vest" category |
| `PPE_GLOVE_CLASSES` | `gloves,glove` | Model class names that map to the "gloves" category |
| `PPE_SHOE_CLASSES` | `boots,safety shoes` | Model class names that map to the "shoes" category |
| `REQUIRED_PPE` | `helmet,vest` | Comma-separated list of required PPE categories |
| `PPE_ASSOCIATION_IOU_THRESHOLD` | `0.10` | Minimum overlap ratio for PPE-to-person association |
| `PPE_MISSING_CONFIRMATION_FRAMES` | `5` | Number of consecutive frames PPE must be absent before a violation is confirmed |
| `PPE_EVENT_COOLDOWN_SECONDS` | `10` | Seconds between repeated violation events for the same worker + PPE item |

### PPE API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/safety/ppe/{job_id}` | PPE compliance summary for a job |
| `GET` | `/api/v1/safety/ppe/{job_id}/workers` | Per-worker PPE compliance details |

### PPE Limitations

- PPE compliance is **heuristic and model-dependent**. Accuracy depends entirely on the quality and training of the PPE detection model.
- The system does **not** claim compliance with OSHA, ISO, or any other occupational safety standard.
- Severity classifications (`high`, `critical`) are application-level labels and do **not** represent legal or regulatory determinations.
- PPE detection accuracy is limited by image resolution, camera angle, occlusion, and lighting conditions.
- Physical distance measurements are in pixel space. Accurate real-world distance requires camera calibration.

---

## Inventory Counting & Monitoring

WarehouseVision AI includes an **Inventory Monitoring subsystem** that tracks and counts configured inventory classes across video frames, records periodic snapshots, detects count changes, and monitors low-stock conditions.

### Architecture Pipeline

```text
Video Frame
     │
     ▼
YOLO Detection + ByteTrack Tracking
     │
     ▼
Tracked Objects (Persons, Forklifts, Inventory)
     │
     ├──► Safety Analyzer (Zones, Proximity, Collision Risk)
     ├──► PPE Analyzer (Worker Gear Compliance)
     │
     ▼
Inventory Analyzer (Filters Configured Classes: box, pallet, crate)
     │
     ▼
Visible Counts & Persistent Unique Track IDs
     │
     ▼
Periodic Snapshots (Recorded every N seconds)
     │
     ├──► Count Change Detection (Delta >= threshold)
     └──► Low-Stock Alerts (Visible count <= threshold)
     │
     ▼
MongoDB Persistence (snapshots, events, job summary)
```

### Critical Counting Distinctions

It is essential to understand the difference between the metrics provided by computer vision and true warehouse stock:

| Metric | What It Means | What It Does NOT Mean |
|---|---|---|
| **Visible Count** | Number of configured inventory objects detected in a single video frame. | Physical stock in the warehouse. Visible counts fluctuate due to occlusion, camera angle, lighting, or motion blur. |
| **Unique Track Count** | Total number of persistent tracker IDs assigned to a class during the video session. | Total warehouse inventory. Tracker identity switches, occlusions, and re-entries can assign multiple track IDs to the same physical object. |
| **Actual Inventory** | Ground-truth physical inventory stored in the warehouse facility. | Cannot be guaranteed purely by single-camera visual inspection; requires reconciliation with barcode, RFID, or WMS systems. |

### Model Availability & Warehouse Domain Classes

- Inventory classes (such as `box`, `pallet`, `crate`) are **model-dependent**.
- Pretrained COCO models (like standard `yolo11n.pt`) do not support warehouse-specific concepts like pallets, racks, or industrial bins.
- At job startup, the `InventoryAnalyzer` inspects the loaded model's class labels and marks unavailable classes cleanly (`available: false` with explanatory reason).
- The system **never fabricates detections** or relabels unrelated classes.

### Snapshots, Count Changes & Low-Stock Alerts

- **Periodic Snapshots**: Captured at configurable intervals (`INVENTORY_SNAPSHOT_INTERVAL_SECONDS`, default: 10s) to record visible counts over time without bloating MongoDB.
- **Count Changes**: Computed across consecutive snapshots. If the difference in visible count exceeds `INVENTORY_CHANGE_THRESHOLD`, an `inventory_count_change` event is generated.
- **Low-Stock Alerts**: If the visible count falls at or below `INVENTORY_THRESHOLDS_JSON`, an `inventory_low_stock` event is produced.
- **Event Deduplication**: Governed by `INVENTORY_EVENT_COOLDOWN_SECONDS` (default: 10s) to prevent generating repeated alert events every frame.

### Inventory Configuration

| Variable | Default | Description |
|---|---|---|
| `INVENTORY_ENABLED` | `true` | Master toggle for inventory monitoring |
| `INVENTORY_CLASSES` | `box,pallet,crate` | Comma-separated list of target inventory classes to track |
| `INVENTORY_CONFIDENCE_THRESHOLD` | `0.40` | Minimum detector confidence for inventory objects |
| `INVENTORY_COUNT_MODE` | `visible` | Primary counting strategy (`visible` or `unique`) |
| `INVENTORY_SNAPSHOT_INTERVAL_SECONDS` | `10` | Frequency in seconds at which periodic inventory snapshots are recorded |
| `INVENTORY_CHANGE_THRESHOLD` | `1` | Minimum count delta between snapshots required to trigger a change event |
| `INVENTORY_LOW_STOCK_ENABLED` | `true` | Toggle for evaluating low-stock alerts |
| `INVENTORY_EVENT_COOLDOWN_SECONDS` | `10` | Cooldown period suppressing duplicate events |
| `INVENTORY_THRESHOLDS_JSON` | `{"box":5,"pallet":2,"crate":3}` | JSON map of class names to minimum stock thresholds |

### Inventory API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/inventory/events` | List inventory events across all user processing jobs (paginated, filterable) |
| `GET` | `/api/v1/inventory/{job_id}` | Cumulative inventory summary and statistics for a specific job |
| `GET` | `/api/v1/inventory/{job_id}/snapshots` | Periodic inventory snapshots for a job (paginated) |
| `GET` | `/api/v1/inventory/{job_id}/events` | Inventory events (count changes, low stock) for a specific job (paginated) |
| `GET` | `/api/v1/processing/{job_id}/result` | Video processing result payload (includes `inventory` summary) |

---

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

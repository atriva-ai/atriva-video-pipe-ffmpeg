# Video Pipeline API Integration Guide

## Overview

This guide explains how to integrate the Video Pipeline API service with other services in the Atriva platform, particularly AI inference containers that consume decoded frames.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Integration Approaches](#integration-approaches)
- [API Reference](#api-reference)
- [Shared Storage Integration](#shared-storage-integration)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)
- [Security Considerations](#security-considerations)

## Architecture Overview

The Video Pipeline service is designed as a standalone microservice that can be integrated with other services through:

1. **REST API** - For control and status queries
2. **Shared Volume Storage** - For frame data access by AI inference containers

### Service Communication

```
┌─────────────────┐
│  Dashboard API  │
│   (Backend)     │
└────────┬────────┘
         │ HTTP/REST
         │
┌────────▼─────────────────┐
│  Video Pipeline Service  │
│   (FFmpeg x86)           │
└────────┬──────────────────┘
         │
         │ Writes frames to
         │ shared volume
         │
┌────────▼─────────────────┐
│   Shared Volume          │
│  /app/frames/            │
│  ├── camera_1/           │
│  └── camera_2/           │
└────────┬──────────────────┘
         │
         │ Read frames from
         │ shared volume
         │
┌────────▼─────────────────┐
│  AI Inference Containers │
│  (YOLO, etc.)            │
└──────────────────────────┘
```

## Integration Approaches

### Option 1: Service-to-Service Communication (Recommended)

The video pipeline remains a standalone service, and other services communicate via REST API.

**Benefits:**
- Service independence
- Scalability
- Technology isolation
- Easy deployment

**Implementation Example:**
```python
# dashboard-backend/app/routes/video_pipeline.py
import httpx
from fastapi import APIRouter, Depends

VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "http://video-pipeline:8002")

@router.post("/camera/{camera_id}/decode/")
async def start_camera_decode(
    camera_id: int,
    url: str,
    fps: int = 1,
    client: httpx.AsyncClient = Depends(get_http_client)
):
    # Forward request to video pipeline service
    response = await client.post(
        f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
        data={
            "camera_id": str(camera_id),
            "url": url,
            "fps": fps
        }
    )
    return response.json()
```

### Option 2: Shared Volume Access (For AI Inference)

AI inference containers can directly access decoded frames from the shared volume without API calls.

**Benefits:**
- Low latency
- No network overhead
- Direct file access
- Efficient for high-throughput scenarios

**Implementation Example:**
```python
# ai-inference-container code
from pathlib import Path
import cv2

FRAMES_DIR = Path("/shared/frames")  # Mounted shared volume

def get_latest_frame(camera_id: str):
    """Get the latest frame for a camera from shared storage"""
    camera_dir = FRAMES_DIR / camera_id
    if not camera_dir.exists():
        return None
    
    # Find latest frame by modification time
    jpg_files = list(camera_dir.glob("*.jpg"))
    if not jpg_files:
        return None
    
    latest = max(jpg_files, key=lambda f: f.stat().st_mtime)
    return cv2.imread(str(latest))
```

## API Reference

### Start Video Decoding

**Endpoint:** `POST /api/v1/video-pipeline/decode/`

Start decoding a video stream and extracting frames.

**Parameters:**
- `camera_id` (string, required): Unique identifier for the camera
- `file` (file, optional): Video file upload
- `url` (string, optional): Video URL (file or RTSP stream)
- `fps` (integer, optional): Frames per second to extract (default: 1)
- `force_format` (string, optional): Force hardware acceleration format (cuda, qsv, vaapi, none)

**Response:**
```json
{
  "message": "Decoding started",
  "camera_id": "camera_1",
  "output_folder": "/app/frames/camera_1",
  "status": "started"
}
```

### Get Decode Status

**Endpoint:** `GET /api/v1/video-pipeline/decode/status/?camera_id={camera_id}`

Get the current status of decoding for a camera.

**Response:**
```json
{
  "camera_id": "camera_1",
  "status": "running",
  "frame_count": 150,
  "last_error": null,
  "restart_count": 0
}
```

### Stop Decoding

**Endpoint:** `POST /api/v1/video-pipeline/decode/stop/`

Stop decoding for a camera.

**Parameters:**
- `camera_id` (string, required): Camera identifier

### Get Latest Frame

**Endpoint:** `GET /api/v1/video-pipeline/latest-frame/?camera_id={camera_id}`

Get the most recent decoded frame as a JPEG image.

**Response:** JPEG image file

### Get Video Information

**Endpoint:** `POST /api/v1/video-pipeline/video-info/`

Get metadata about a video file.

**Parameters:**
- `video` (file, required): Video file upload

**Response:**
```json
{
  "message": "Video information retrieved",
  "info": {
    "format": "rtsp",
    "codec": "h264",
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "duration": 0.0
  }
}
```

### Hardware Acceleration Capabilities

**Endpoint:** `GET /api/v1/video-pipeline/hw-accel-cap/`

Check available hardware acceleration options.

**Response:**
```json
{
  "message": {
    "available_hw_accelerations": ["cuda", "qsv", "vaapi"]
  }
}
```

### Health Check

**Endpoint:** `GET /api/v1/video-pipeline/health/`

Check service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "video-pipeline"
}
```

## Shared Storage Integration

### Volume Structure

The shared volume follows this structure:

```
/shared/frames/              # Mount point (configurable)
├── {camera_id_1}/
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   ├── frame_0003.jpg
│   └── ...
├── {camera_id_2}/
│   ├── frame_0001.jpg
│   └── ...
└── ...
```

### Frame Naming Convention

Frames are named sequentially: `frame_%04d.jpg` (e.g., `frame_0001.jpg`, `frame_0002.jpg`)

### Accessing Frames in AI Inference Containers

1. **Mount the shared volume** in your Docker Compose or Kubernetes deployment
2. **Read frames directly** from the filesystem
3. **Monitor frame updates** by checking file modification times

**Docker Compose Example:**
```yaml
services:
  video-pipeline:
    volumes:
      - shared-frames:/app/frames
  
  ai-inference:
    volumes:
      - shared-frames:/shared/frames  # Same volume, different mount point
    depends_on:
      - video-pipeline

volumes:
  shared-frames:
```

## Configuration

### Environment Variables

```bash
# Service Configuration
VIDEO_PIPELINE_URL=http://video-pipeline:8002

# FFmpeg Configuration
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe
HW_ACCEL_OPTIONS=["cuda", "qsv", "vaapi", "none"]

# Storage Paths (inside container)
UPLOAD_FOLDER=/app/videos
OUTPUT_FOLDER=/app/frames
```

### Docker Compose Integration

```yaml
services:
  video-pipeline:
    build: ./video-pipeline-ffmpeg-x86
    ports:
      - "8002:8002"
    volumes:
      - shared-frames:/app/frames
      - video-storage:/app/videos
    environment:
      - FFMPEG_PATH=ffmpeg
      - FFPROBE_PATH=ffprobe
    devices:
      - /dev/dri:/dev/dri  # For VAAPI

  ai-inference:
    build: ./ai-inference
    volumes:
      - shared-frames:/shared/frames
    depends_on:
      - video-pipeline

volumes:
  shared-frames:
  video-storage:
```

## Usage Examples

### 1. Start Decoding RTSP Stream

```bash
curl -X POST "http://localhost:8002/api/v1/video-pipeline/decode/" \
  -F "camera_id=camera_1" \
  -F "url=rtsp://camera.example.com/stream" \
  -F "fps=5"
```

### 2. Check Decoding Status

```bash
curl "http://localhost:8002/api/v1/video-pipeline/decode/status/?camera_id=camera_1"
```

### 3. Get Latest Frame via API

```bash
curl "http://localhost:8002/api/v1/video-pipeline/latest-frame/?camera_id=camera_1" \
  --output latest_frame.jpg
```

### 4. Access Frame from Shared Volume (Python)

```python
from pathlib import Path
from PIL import Image

frames_dir = Path("/shared/frames")
camera_dir = frames_dir / "camera_1"

# Get latest frame
jpg_files = sorted(camera_dir.glob("*.jpg"))
if jpg_files:
    latest_frame = Image.open(jpg_files[-1])
    # Process frame...
```

## Error Handling

### Common Error Scenarios

1. **Camera Not Found**: Return 404 if camera_id doesn't exist
2. **Service Unavailable**: Return 503 if video pipeline is down
3. **Decoding Failed**: Check `last_error` in status response
4. **No Frames Available**: Return 404 if no frames exist for camera

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

## Security Considerations

1. **Authentication**: Add JWT token validation for API access
2. **Authorization**: Verify user permissions for camera operations
3. **Input Validation**: Sanitize file uploads and URLs
4. **Rate Limiting**: Implement request throttling
5. **CORS**: Configure cross-origin requests appropriately
6. **Volume Permissions**: Ensure proper file permissions on shared volumes

## Monitoring and Logging

### Health Checks

Implement periodic health checks:

```python
async def check_video_pipeline_health():
    try:
        response = await client.get(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/health/")
        return response.json()["status"] == "healthy"
    except Exception:
        return False
```

### Logging Best Practices

- Log all decode start/stop events
- Log frame extraction counts
- Log errors with camera_id context
- Monitor shared volume disk usage

## Troubleshooting

### Common Issues

1. **Service Unavailable**: Check container status and logs
2. **No Frames Generated**: Verify video source is accessible
3. **Permission Errors**: Check shared volume mount permissions
4. **Hardware Acceleration Failures**: Verify GPU drivers and device access

### Debug Commands

```bash
# Check service logs
docker logs video-pipeline

# Verify FFmpeg installation
docker exec video-pipeline ffmpeg -version

# Check hardware acceleration
curl http://localhost:8002/api/v1/video-pipeline/hw-accel-cap/

# List frames in shared volume
ls -la /path/to/shared/frames/camera_1/
```

## Future Enhancements

1. **WebSocket Support**: Real-time processing status updates
2. **Batch Processing**: Process multiple videos simultaneously
3. **Frame Caching**: Implement LRU cache for frequently accessed frames
4. **Storage Management**: Automatic cleanup of old frames
5. **Metrics Export**: Prometheus metrics for monitoring

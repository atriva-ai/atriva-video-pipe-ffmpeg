# Testing Guide

## Testing Overview

This guide covers testing procedures for the Video Pipeline service, including unit tests, integration tests, and manual testing procedures.

## Test Types

### Unit Tests

Test individual functions and components in isolation.

### Integration Tests

Test API endpoints and service interactions.

### Manual Testing

Test with real video files and streams.

## Running Tests

### Setup Test Environment

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Create test directories
mkdir -p test_frames test_videos
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_routes.py
```

## Test Examples

### Testing Video Info Endpoint

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_video_info():
    with open("test_videos/sample.mp4", "rb") as f:
        response = client.post(
            "/api/v1/video-pipeline/video-info/",
            files={"video": ("sample.mp4", f, "video/mp4")}
        )
    assert response.status_code == 200
    assert "info" in response.json()
```

### Testing Decode Endpoint

```python
def test_decode_video():
    response = client.post(
        "/api/v1/video-pipeline/decode/",
        data={
            "camera_id": "test_camera",
            "url": "rtsp://test.example.com/stream",
            "fps": 1
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "started"
```

## Manual Testing Procedures

### 1. Health Check

```bash
curl http://localhost:8002/api/v1/video-pipeline/health/
```

**Expected:** `{"status": "healthy", "service": "video-pipeline"}`

### 2. Hardware Acceleration Check

```bash
curl http://localhost:8002/api/v1/video-pipeline/hw-accel-cap/
```

**Expected:** List of available hardware acceleration methods

### 3. Video Information

```bash
curl -X POST "http://localhost:8002/api/v1/video-pipeline/video-info/" \
  -F "video=@test_video.mp4"
```

**Expected:** Video metadata including codec, resolution, FPS

### 4. Start Decoding

```bash
curl -X POST "http://localhost:8002/api/v1/video-pipeline/decode/" \
  -F "camera_id=test_camera_1" \
  -F "url=rtsp://example.com/stream" \
  -F "fps=5"
```

**Expected:** Decode task started successfully

### 5. Check Decode Status

```bash
curl "http://localhost:8002/api/v1/video-pipeline/decode/status/?camera_id=test_camera_1"
```

**Expected:** Status information including frame count

### 6. Get Latest Frame

```bash
curl "http://localhost:8002/api/v1/video-pipeline/latest-frame/?camera_id=test_camera_1" \
  --output latest_frame.jpg
```

**Expected:** JPEG image file

### 7. Stop Decoding

```bash
curl -X POST "http://localhost:8002/api/v1/video-pipeline/decode/stop/" \
  -F "camera_id=test_camera_1"
```

**Expected:** Decode stopped successfully

## Test Data

### Sample Videos

Use test videos with various:
- Formats (MP4, AVI, MOV)
- Codecs (H.264, H.265, MPEG-4)
- Resolutions (720p, 1080p, 4K)
- Frame rates (24fps, 30fps, 60fps)

### RTSP Streams

For RTSP testing, use:
- Test RTSP servers (e.g., `rtsp://test.example.com/stream`)
- Local RTSP streams from cameras
- RTSP test tools

## Performance Testing

### Load Testing

Test with multiple concurrent decode requests:

```bash
# Using Apache Bench
ab -n 100 -c 10 -p decode_request.json \
  -T application/json \
  http://localhost:8002/api/v1/video-pipeline/decode/
```

### Stress Testing

Test system behavior under load:
- Multiple cameras decoding simultaneously
- High FPS extraction rates
- Large video files

## Integration Testing with AI Containers

### Test Shared Volume Access

1. Start video pipeline container
2. Start decode for a camera
3. Verify frames appear in shared volume
4. Test AI container reading frames

### Test Frame Consumption

```python
# In AI inference container test
from pathlib import Path
import time

frames_dir = Path("/shared/frames/camera_1")
initial_count = len(list(frames_dir.glob("*.jpg")))

# Wait for new frames
time.sleep(10)

final_count = len(list(frames_dir.glob("*.jpg")))
assert final_count > initial_count
```

## Troubleshooting Test Failures

### Common Issues

1. **Port already in use**: Change port or stop existing service
2. **Missing test files**: Ensure test videos exist
3. **Permission errors**: Check volume mount permissions
4. **FFmpeg errors**: Verify FFmpeg installation and hardware support

### Debug Test Failures

```bash
# Run tests with verbose output
pytest -v

# Run with print statements
pytest -s

# Run specific test with debugging
pytest tests/test_specific.py::test_function -v -s
```

## Continuous Integration

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest
```

## Test Coverage

Aim for:
- 80%+ code coverage
- All API endpoints tested
- Critical paths covered
- Error cases tested

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Clean up**: Remove test data after tests
3. **Use fixtures**: Reuse common test setup
4. **Mock external services**: Don't depend on external services in unit tests
5. **Test error cases**: Verify error handling works correctly


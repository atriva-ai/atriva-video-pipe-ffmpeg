from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional
from pathlib import Path
from app.services.ffmpeg_utils import decode_video2frames_in_jpeg, capture_snapshot, record_clip, get_video_info, get_all_hwaccel
from app.models.schemas import SnapshotRequest, RecordRequest
from config import UPLOAD_FOLDER, OUTPUT_FOLDER
import requests

# Create router with prefix and tags for better organization
router = APIRouter(
    prefix="/api/v1/video-pipeline",
    tags=["Video Pipeline"]
)

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)  # Ensure the folder exists
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

def download_video(url: str, save_path: Path):
    """Download a video file from a given URL and save it locally."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Ensure the request was successful

        with save_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return save_path
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")

@router.post("/video-info/")
async def video_info(video: UploadFile = File(...)):
    """Get video metadata and information"""
    file_path = UPLOAD_FOLDER / video.filename
    print('Getting video file: {file_path}')
    # Save the uploaded file
    with file_path.open("wb") as buffer:
        buffer.write(await video.read())
    print(f"File uploaded successfully to {str(file_path)}")
    print("Getting video info...")
    info = get_video_info(file_path)
    if info["codec"]:
        return {"message": "Video information retrieved", "info": info}
    raise HTTPException(status_code=500, detail="Could not retrieve video information")

@router.get("/hw-accel-cap/")
async def hw_accel_cap():
    """Check available hardware acceleration options"""
    result = get_all_hwaccel()
    return {"message": result}

@router.post("/decode/")
async def decode_video(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    fps: Optional[int] = Form(1),  # Default FPS is 1 frame per second
    force_format: Optional[str] = Form(None)
):
    """Process a video file from either an uploaded file or a URL and extract frames at specified FPS."""
    if not file and not url:
        raise HTTPException(status_code=400, detail="Either a file or a URL must be provided.")

    # Handle file upload
    if file:
        input_path = UPLOAD_FOLDER / file.filename
        print("Decoding video file: {input_path}")
        with input_path.open("wb") as buffer:
            buffer.write(await file.read())

    # Handle URL input
    elif url:
        filename = url.split("/")[-1]  # Extract filename from URL
        print("Decoding video URL: {filename}")
        input_path = UPLOAD_FOLDER / filename
        input_path = download_video(url, input_path)  # Download the video

    # Process the video
    try:
        output_folder = decode_video2frames_in_jpeg(str(input_path), str(OUTPUT_FOLDER), force_format, fps)
        return {"message": "Video processed successfully", "output_folder": output_folder}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/snapshot/")
async def snapshot(request: SnapshotRequest):
    """Capture a snapshot from video at specified timestamp"""
    result = capture_snapshot(request.video_url, request.timestamp, request.output_image)
    if result.returncode == 0:
        return {"message": "Snapshot captured", "output": request.output_image}
    raise HTTPException(status_code=500, detail=result.stderr)

@router.post("/record/")
async def record(request: RecordRequest):
    """Record a video clip from specified start time and duration"""
    result = record_clip(request.video_url, request.start_time, request.duration, request.output_path)
    if result.returncode == 0:
        return {"message": "Recording successful", "output": request.output_path}
    raise HTTPException(status_code=500, detail=result.stderr)

# Health check endpoint
@router.get("/health/")
async def health_check():
    """Health check for video pipeline service"""
    return {"status": "healthy", "service": "video-pipeline"}

# Debug endpoint
@router.get("/debug/")
async def debug_info():
    """Debug information for video pipeline service"""
    import socket
    import os
    return {
        "status": "running",
        "service": "video-pipeline",
        "hostname": socket.gethostname(),
        "port": 8002,
        "environment": {
            "FFMPEG_PATH": os.getenv("FFMPEG_PATH", "ffmpeg"),
            "FFPROBE_PATH": os.getenv("FFPROBE_PATH", "ffprobe")
        }
    }
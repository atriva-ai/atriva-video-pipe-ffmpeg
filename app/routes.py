from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Optional, Dict
from pathlib import Path
from app.services.ffmpeg_utils import decode_video2frames_in_jpeg, capture_snapshot, record_clip, get_video_info, get_all_hwaccel
from app.models.schemas import SnapshotRequest, RecordRequest
from config import UPLOAD_FOLDER, OUTPUT_FOLDER
import requests
import subprocess
import os
import threading
import shutil
import time
from fastapi.responses import FileResponse

# Create router with prefix and tags for better organization
router = APIRouter(
    prefix="/api/v1/video-pipeline",
    tags=["Video Pipeline"]
)

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)  # Ensure the folder exists
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

# Global decode task manager
# Structure: { camera_id: { 'process': Popen, 'output_folder': str, 'status': str, 'last_error': str|None } }
decode_tasks: Dict[str, dict] = {}
task_lock = threading.Lock()

def cleanup_camera_frames(camera_id: str):
    """Clean up all frames for a specific camera"""
    try:
        camera_folder = OUTPUT_FOLDER / camera_id
        if camera_folder.exists():
            # Remove all .jpg files in the camera folder
            for file in camera_folder.glob("*.jpg"):
                file.unlink()
            print(f"Cleaned up frames for camera {camera_id}")
    except Exception as e:
        print(f"Error cleaning up frames for camera {camera_id}: {e}")

def cleanup_orphaned_frames():
    """Clean up frames for cameras that no longer exist in decode_tasks"""
    try:
        # Get all camera folders
        for camera_folder in OUTPUT_FOLDER.iterdir():
            if camera_folder.is_dir():
                camera_id = camera_folder.name
                # Check if this camera is still in active decode tasks
                with task_lock:
                    if camera_id not in decode_tasks or decode_tasks[camera_id]['status'] == 'stopped':
                        # Camera is not active, clean up its frames
                        cleanup_camera_frames(camera_id)
    except Exception as e:
        print(f"Error cleaning up orphaned frames: {e}")

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

@router.post("/video-info-url/")
async def video_info_url(url: str = Form(...)):
    """Get video metadata and information from URL"""
    print(f"Getting video info from URL: {url}")
    info = get_video_info(url)
    if info.get("codec") and "error" not in info:
        return {"message": "Video information retrieved", "info": info}
    raise HTTPException(status_code=500, detail=f"Could not retrieve video information: {info.get('error', 'Unknown error')}")

@router.get("/hw-accel-cap/")
async def hw_accel_cap():
    """Check available hardware acceleration options"""
    result = get_all_hwaccel()
    return {"message": result}

def get_frame_count(output_folder):
    try:
        return len([f for f in os.listdir(output_folder) if f.endswith('.jpg')])
    except Exception:
        return 0

def is_process_running(proc):
    return proc and proc.poll() is None

def restart_decode_process(camera_id: str, task: dict) -> bool:
    """
    Attempt to restart a stopped decode process.
    Returns True if restart was successful, False otherwise.
    """
    proc = task.get('process')
    if not proc:
        return False
    
    return_code = proc.poll()
    input_url = task.get('input_url', '')
    
    # For RTSP streams, auto-restart if process stopped
    if input_url and input_url.startswith('rtsp://'):
        restart_count = task.get('restart_count', 0)
        max_restarts = 10  # Max auto-restarts before giving up
        
        if restart_count >= max_restarts:
            task['status'] = 'error'
            task['last_error'] = f"Max restarts ({max_restarts}) reached"
            print(f"Decoder for camera {camera_id} exceeded max restarts")
            return False
        
        print(f"RTSP decoder for camera {camera_id} stopped (code {return_code}), auto-restarting... (attempt {restart_count + 1})")
        
        # Restart the decoder
        output_folder = Path(task['output_folder'])
        fps = task.get('fps', 1)
        
        ffmpeg_cmd = [
            "ffmpeg", 
            "-rtsp_transport", "tcp",
            "-timeout", "5000000",
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "2",
            "-i", input_url,
            "-vf", f"fps={fps},format=rgb24",
            "-q:v", "2",
            f"{output_folder}/frame_%04d.jpg"
        ]
        
        try:
            new_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            task['process'] = new_proc
            task['status'] = 'running'
            task['restart_count'] = restart_count + 1
            task['last_error'] = None
            print(f"Decoder restarted for camera {camera_id}, new PID: {new_proc.pid}")
            return True
        except Exception as e:
            task['status'] = 'error'
            task['last_error'] = f"Auto-restart failed: {str(e)}"
            print(f"Failed to restart decoder for camera {camera_id}: {e}")
            return False
    else:
        # Non-RTSP stream - check if it's a mediaMTX stream that should be restarted
        # mediaMTX streams through RTSP should always restart, even if they exit with code 0
        # (which happens when a file loops)
        if 'localhost:8554' in input_url or 'mediamtx' in input_url.lower() or '8554' in input_url:
            # This is likely a mediaMTX stream - restart it even if it exited successfully
            print(f"mediaMTX stream for camera {camera_id} stopped (code {return_code}), restarting...")
            restart_count = task.get('restart_count', 0)
            max_restarts = 100  # Allow many restarts for looping streams
            
            if restart_count >= max_restarts:
                task['status'] = 'error'
                task['last_error'] = f"Max restarts ({max_restarts}) reached"
                print(f"Decoder for camera {camera_id} exceeded max restarts")
                return False
            
            # Restart with same settings
            output_folder = Path(task['output_folder'])
            fps = task.get('fps', 1)
            
            ffmpeg_cmd = [
                "ffmpeg", 
                "-rtsp_transport", "tcp",
                "-timeout", "5000000",
                "-reconnect", "1",
                "-reconnect_at_eof", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "2",
                "-i", input_url,
                "-vf", f"fps={fps},format=rgb24",
                "-q:v", "2",
                f"{output_folder}/frame_%04d.jpg"
            ]
            
            try:
                new_proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                task['process'] = new_proc
                task['status'] = 'running'
                task['restart_count'] = restart_count + 1
                task['last_error'] = None
                print(f"mediaMTX decoder restarted for camera {camera_id}, new PID: {new_proc.pid}")
                return True
            except Exception as e:
                task['status'] = 'error'
                task['last_error'] = f"Auto-restart failed: {str(e)}"
                print(f"Failed to restart mediaMTX decoder for camera {camera_id}: {e}")
                return False
        else:
            # Non-RTSP, non-mediaMTX stream - mark as completed/error normally
            if return_code == 0:
                task['status'] = 'completed'
                print(f"Decode process completed successfully for camera {camera_id}")
            else:
                task['status'] = 'error'
                task['last_error'] = f"Process exited with code {return_code}"
                print(f"Decode process failed for camera {camera_id} with code {return_code}")
            return False

def check_and_restart_decode_processes():
    """
    Check all active decode processes and restart any that have stopped.
    This function should be called periodically in the background.
    """
    cameras_to_check = []
    with task_lock:
        # Get a copy of camera IDs to check
        cameras_to_check = list(decode_tasks.keys())
    
    if not cameras_to_check:
        return  # No active tasks to monitor
    
    for camera_id in cameras_to_check:
        with task_lock:
            task = decode_tasks.get(camera_id)
            if not task:
                continue
            
            # Only check processes that are marked as running
            if task['status'] != 'running':
                continue
            
            proc = task.get('process')
            if not proc:
                continue
            
            # Check if process is still running
            running = is_process_running(proc)
            
            if not running:
                # Process stopped - get return code and log it
                return_code = proc.poll()
                input_url = task.get('input_url', 'unknown')
                print(f"🔍 Monitor detected stopped process for camera {camera_id} (return code: {return_code}, input: {input_url})")
                # Process stopped - attempt restart
                restart_success = restart_decode_process(camera_id, task)
                if restart_success:
                    print(f"✅ Successfully restarted decode process for camera {camera_id}")
                else:
                    print(f"❌ Failed to restart decode process for camera {camera_id}")

@router.post("/decode/")
async def decode_video(
    camera_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    fps: Optional[int] = Form(1),
    force_format: Optional[str] = Form(None)
):
    """Start decoding for a camera and register the process."""
    if not file and not url:
        raise HTTPException(status_code=400, detail="Either a file or a URL must be provided.")

    # Check if a decode task already exists for this camera
    with task_lock:
        existing_task = decode_tasks.get(camera_id)
        if existing_task and existing_task['process'] and is_process_running(existing_task['process']):
            return {
                "message": "Decoding already running", 
                "camera_id": camera_id, 
                "output_folder": existing_task['output_folder'],
                "status": "already_running"
            }
        elif existing_task and existing_task['status'] == 'running':
            return {
                "message": "Decoding already running", 
                "camera_id": camera_id, 
                "output_folder": existing_task['output_folder'],
                "status": "already_running"
            }

    # Prepare input
    if file:
        input_path = UPLOAD_FOLDER / file.filename
        print(f"Decoding video file: {input_path}")
        with input_path.open("wb") as buffer:
            buffer.write(await file.read())
    elif url:
        print(f"Decoding video URL: {url}")
        input_path = url

    # Prepare output folder for this camera
    output_folder = OUTPUT_FOLDER / camera_id
    output_folder.mkdir(parents=True, exist_ok=True)

    # Clean up any existing frames for this camera before starting new decode
    cleanup_camera_frames(camera_id)

    try:
        # Run ffmpeg decode asynchronously in a subprocess
        print(f"Starting decode for camera {camera_id} with input: {input_path}")
        
        # Build ffmpeg command
        input_path_str = str(input_path)
        if input_path_str.startswith('rtsp://'):
            # RTSP-specific options for better stability:
            # -rtsp_transport tcp: Use TCP for more reliable connection
            # -timeout 5000000: Connection timeout 5 seconds (in microseconds)
            # -reconnect_on_network_error 1: Try to reconnect on network errors
            # -fflags +genpts: Generate missing PTS for smoother playback
            # -stream_loop -1: Loop the input stream indefinitely (for mediaMTX file-based streams)
            ffmpeg_cmd = [
                "ffmpeg", 
                "-rtsp_transport", "tcp",
                "-timeout", "5000000",
                "-reconnect", "1",
                "-reconnect_at_eof", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "2",
                "-i", input_path_str,
                "-vf", f"fps={fps},format=rgb24",
                "-q:v", "2",  # High quality JPEG
                f"{output_folder}/frame_%04d.jpg"
            ]
        else:
            ffmpeg_cmd = [
                "ffmpeg", "-i", input_path_str,
                "-vf", f"fps={fps},format=rgb24",
                "-q:v", "2",
                f"{output_folder}/frame_%04d.jpg"
            ]
        
        print(f"Running ffmpeg command: {ffmpeg_cmd}")
        proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Store input URL for potential restart
        input_url = input_path_str
        
        # Register the task as running
        with task_lock:
            decode_tasks[camera_id] = {
                'process': proc,
                'output_folder': str(output_folder),
                'status': 'running',
                'last_error': None,
                'input_url': input_url,
                'fps': fps,
                'restart_count': 0
            }
        
        print(f"Decode started for camera {camera_id}, process PID: {proc.pid}")
        return {
            "message": "Decoding started", 
            "camera_id": camera_id, 
            "output_folder": str(output_folder),
            "status": "started"
        }
        
    except Exception as e:
        error_msg = f"Failed to start decode: {str(e)}"
        print(f"Error in decode for camera {camera_id}: {error_msg}")
        with task_lock:
            decode_tasks[camera_id] = {
                'process': None,
                'output_folder': str(output_folder),
                'status': 'error',
                'last_error': error_msg,
                'input_url': str(input_path) if 'input_path' in locals() else None,
                'fps': fps,
                'restart_count': 0
            }
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/decode/stop/")
async def stop_decode(camera_id: str = Form(...)):
    """Stop decoding for a camera."""
    with task_lock:
        task = decode_tasks.get(camera_id)
        if not task:
            # No task exists - already stopped, just clean up frames and return success
            print(f"No decode task found for camera {camera_id}, already stopped")
            cleanup_camera_frames(camera_id)
            return {"message": "Decoding stopped (no task was running)", "camera_id": camera_id}
        
        proc = task['process']
        if proc is None:
            # Synchronous decode completed - just mark as stopped
            task['status'] = 'stopped'
            print(f"Marked synchronous decode task as stopped for camera {camera_id}")
            # Clean up frames when stopping
            cleanup_camera_frames(camera_id)
            return {"message": "Decoding stopped", "camera_id": camera_id}
        
        # Handle subprocess-based decoding
        if is_process_running(proc):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        task['status'] = 'stopped'
        
        # Clean up frames when stopping
        cleanup_camera_frames(camera_id)
        return {"message": "Decoding stopped", "camera_id": camera_id}

@router.get("/decode/status/")
async def decode_status(camera_id: str):
    """Get the status of the decode task for a camera."""
    with task_lock:
        task = decode_tasks.get(camera_id)
        if not task:
            return {"camera_id": camera_id, "status": "not_started", "frame_count": 0}
        
        proc = task['process']
        if proc is None:
            # No process (error or not started)
            frame_count = get_frame_count(task['output_folder'])
            return {
                "camera_id": camera_id,
                "status": task['status'],
                "frame_count": frame_count,
                "last_error": task.get('last_error')
            }
        
        # Check if subprocess is still running
        running = is_process_running(proc)
        frame_count = get_frame_count(task['output_folder'])
        
        # Check for stale frames if status is running
        if task['status'] == 'running' and frame_count > 0:
            output_folder = Path(task['output_folder'])
            try:
                jpg_files = list(output_folder.glob("*.jpg"))
                if jpg_files:
                    latest_frame_path = max(jpg_files, key=lambda f: f.stat().st_mtime)
                    current_time = time.time()
                    frame_mtime = latest_frame_path.stat().st_mtime
                    frame_age = current_time - frame_mtime
                    
                    # If frames are very old (>5 minutes), mark as error
                    if frame_age > 300:
                        task['status'] = 'error'
                        task['last_error'] = f"Stream disconnected - no new frames for {frame_age:.1f}s"
                        print(f"Camera {camera_id} marked as error: frames are {frame_age:.1f}s old")
                        # Clean up stale frames
                        cleanup_camera_frames(camera_id)
                        frame_count = 0
            except Exception as e:
                print(f"Error checking frame age for camera {camera_id}: {e}")
        
        # Update status if process completed/stopped
        if not running and task['status'] == 'running':
            # Use the shared restart function
            restart_decode_process(camera_id, task)
        
        return {
            "camera_id": camera_id,
            "status": task['status'],
            "frame_count": frame_count,
            "last_error": task.get('last_error'),
            "restart_count": task.get('restart_count', 0)
        }

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

@router.post("/cleanup/")
async def cleanup_frames(camera_id: Optional[str] = Form(None)):
    """Clean up frames for a specific camera or all orphaned frames"""
    if camera_id:
        cleanup_camera_frames(camera_id)
        return {"message": f"Cleaned up frames for camera {camera_id}"}
    else:
        cleanup_orphaned_frames()
        return {"message": "Cleaned up all orphaned frames"}

@router.get("/latest-frame/")
async def get_latest_frame(camera_id: str):
    """Get the latest decoded frame for a camera"""
    with task_lock:
        task = decode_tasks.get(camera_id)
        if not task:
            raise HTTPException(status_code=404, detail="No decode task found for this camera.")
        
        output_folder = Path(task['output_folder'])
        if not output_folder.exists():
            raise HTTPException(status_code=404, detail="Output folder does not exist for this camera.")
        
        # Get all jpg files and find the latest one by modification time
        jpg_files = list(output_folder.glob("*.jpg"))
        if not jpg_files:
            raise HTTPException(status_code=404, detail="No frames available. Camera may not be streaming.")
        
        # Find the most recent frame by modification time
        latest_frame_path = max(jpg_files, key=lambda f: f.stat().st_mtime)
        
        # Check if the latest frame is too old (more than 60 seconds for active streaming)
        current_time = time.time()
        frame_mtime = latest_frame_path.stat().st_mtime
        frame_age = current_time - frame_mtime
        
        if frame_age > 60:  # 1 minute = 60 seconds
            # Frame is stale - decoder may have stopped
            print(f"Warning: Latest frame for camera {camera_id} is {frame_age:.1f}s old")
            
            # Check if process is still running
            proc = task.get('process')
            if proc and not is_process_running(proc):
                print(f"Decoder process for camera {camera_id} has stopped")
                # Attempt to restart if it's an RTSP stream
                if task.get('status') == 'running':
                    restart_decode_process(camera_id, task)
                else:
                    task['status'] = 'stopped'
            
            # If frame is very old (>5 minutes), clean up and mark as stopped
            if frame_age > 300:
                print(f"Cleaning up stale frames for camera {camera_id}")
                cleanup_camera_frames(camera_id)
                # Update task status to reflect that streaming has stopped
                if task.get('status') == 'running':
                    task['status'] = 'error'
                    task['last_error'] = f"Stream disconnected - no frames for {frame_age:.1f}s"
                    print(f"Marked camera {camera_id} as error due to stale frames")
                raise HTTPException(status_code=404, detail="Stream appears to be disconnected. Please restart the camera.")
        
        return FileResponse(latest_frame_path)
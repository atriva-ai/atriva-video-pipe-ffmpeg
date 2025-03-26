import subprocess
import ffmpeg
from config import FFMPEG_PATH, HW_ACCEL_OPTIONS

def get_video_info(input_url: str):
    """Retrieve video format, resolution, frame rate, codec, etc."""
    command = [
        FFMPEG_PATH, "-i", input_url
    ]
    
    try:
        result = subprocess.run(command, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        output = e.stderr  # FFmpeg outputs errors in stderr for `-i`
    else:
        output = result.stderr

    video_info = {
        "format": None,
        "resolution": None,
        "frame_rate": None,
        "codec": None
    }

    # Parse the FFmpeg output for video information
    for line in output.split("\n"):
        if "Stream #0" in line and "Video" in line:
            parts = line.split(",")
            for part in parts:
                if "fps" in part:
                    video_info["frame_rate"] = part.strip()
                elif "x" in part and " [" not in part:
                    video_info["resolution"] = part.strip()
                elif "Video:" in part:
                    video_info["codec"] = part.split(" ")[1]
    
    print(f"Stream info: {video_info}")
    return video_info

def get_all_hwaccel():
    """Check available hardware acceleration options on an x86 platform"""
    command = [FFMPEG_PATH, "-hwaccels"]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=True)
        hw_accels = result.stdout.strip().split("\n")[1:]  # Ignore the first line
    except subprocess.CalledProcessError:
        hw_accels = []

    print(f"Hardware acceleration: {hw_accels}")
    return {"available_hw_accelerations": hw_accels}

'''
def get_best_hwaccel():
    hw_accels = ["cuda", "qsv", "vaapi", "vdpau", "vulkan", "opencl", "drm"]
    for accel in hw_accels:
        try:
            ffmpeg.input("input.mp4", hwaccel=accel).output("test.mp4").run()
            return accel  # Return the first working option
        except ffmpeg.Error:
            continue
    return None  # No hardware acceleration available
# best_accel = get_best_hwaccel()
# print(f"Using {best_accel} for hardware acceleration")
'''

def get_best_hwaccel(force_format=None):
    """Check available hardware acceleration and return the best option."""
    if force_format and force_format in HW_ACCEL_OPTIONS:
        return force_format  # Use the forced format if specified and valid
    for accel in HW_ACCEL_OPTIONS:
        try:
            result = subprocess.run(
                [FFMPEG_PATH, "-hwaccel", accel, "-version"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return accel
        except FileNotFoundError:
            continue
    return None  # No available acceleration

def decode_video(input_url: str, output_path: str, force_format: str = None):
    """Decode video using the best available hardware acceleration."""
    hw_accel = get_best_hwaccel(force_format)
    
    if not hw_accel:
        raise RuntimeError("No supported hardware acceleration found.")

    codec_map = {
        "cuda": "h264_nvenc",
        "qsv": "h264_qsv",
        "vaapi": "h264_vaapi"
    }
    
    filter_map = {
        "cuda": "format=yuv420p",
        "qsv": "format=nv12",
        "vaapi": "format=nv12|vaapi,hwupload"
    }

    command = [
        FFMPEG_PATH, "-hwaccel", hw_accel, "-i", input_url,
        "-vf", filter_map[hw_accel],
        "-c:v", codec_map[hw_accel],
        output_path
    ]

    return subprocess.run(command, capture_output=True, text=True)

def capture_snapshot(input_url: str, timestamp: str, output_image: str):
    """Capture image snapshot at a given timestamp"""
    command = [
        FFMPEG_PATH, "-i", input_url, "-ss", timestamp,
        "-frames:v", "1", output_image
    ]
    return subprocess.run(command, capture_output=True, text=True)

def record_clip(input_url: str, start_time: str, duration: str, output_path: str):
    """Record a video clip from a given timestamp and duration"""
    command = [
        FFMPEG_PATH, "-i", input_url, "-ss", start_time,
        "-t", duration, "-c:v", "copy", "-c:a", "copy", output_path
    ]
    return subprocess.run(command, capture_output=True, text=True)

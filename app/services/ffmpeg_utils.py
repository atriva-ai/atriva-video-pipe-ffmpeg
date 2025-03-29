import subprocess, json
from config import FFMPEG_PATH, FFPROBE_PATH, HW_ACCEL_OPTIONS, OUTPUT_FOLDER
from pathlib import Path

def get_video_info(input_url: str):
    """Retrieve video format, resolution, frame rate, codec, etc."""
    command = [
        FFPROBE_PATH, "-v", "error",
        "-select_streams", "v:0",  # Select only the first video stream
        "-show_entries", "format=format_name:stream=codec_name,width,height,avg_frame_rate,duration",
        "-of", "json",
        input_url
    ]
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)

        if "format" not in metadata or "streams" not in metadata:
            raise ValueError("Invalid metadata response from ffprobe")

        video_info = {
            "format": metadata["format"].get("format_name", "unknown"),
            "codec": metadata["streams"][0].get("codec_name", "unknown"),
            "width": metadata["streams"][0].get("width", "unknown"),
            "height": metadata["streams"][0].get("height", "unknown"),
            "fps": eval(metadata["streams"][0].get("avg_frame_rate", "0/1")),  # Convert "30/1" to float
            "duration": float(metadata["format"].get("duration", 0.0))
        }
    
        print(f"Stream info: {video_info}")
        return video_info  # Ensure function returns the extracted metadata
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        print(f"Error extracting video info: {str(e)}")
        return {"error": f"Failed to get video info: {str(e)}"}

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

def get_best_hwaccel(force_format=None):
    """Check available hardware acceleration and return the best option."""
    if force_format and force_format in HW_ACCEL_OPTIONS:
        return force_format  # Use the forced format if specified and valid
    for accel in HW_ACCEL_OPTIONS:
        try:
            # Test if the hardware acceleration works by running a simple ffmpeg probe
            test_command = [
                FFMPEG_PATH, "-hwaccel", accel, "-f", "lavfi", "-i", "nullsrc", "-frames:v", "1", "-f", "null", "-"
            ]
            result = subprocess.run(test_command, capture_output=True, text=True)

            # A working hwaccel should return success (exit code 0)
            if result.returncode == 0:
                print(f"✅ {accel} is supported!")
                return accel
        except FileNotFoundError:
            continue
    return None  # No available acceleration

def decode_video2frames_in_jpeg(input_path: str, output_path: str, force_format: str = "none", fps: int = 1):
    """Decode video and extract frames as JPEG at specified FPS."""
    hw_accel = get_best_hwaccel(force_format)
    if not hw_accel:
        raise RuntimeError("No supported hardware acceleration found.")
    print(f"Transcoding videos to JPEGs using HW mode: {hw_accel}")
    
    # get video info
    print(f"Getting video info from input: {input_path}")
    v_info = get_video_info(input_path)
    print(f"Video format: {v_info["format"]}, codec: {v_info["codec"]}, width: {v_info["width"]}, height: {v_info["height"]}, fps: {v_info["fps"]}")

    # Ensure the output folder exists for this specific video
    video_name = Path(input_path).stem  # Extract filename without extension
    video_output_folder = OUTPUT_FOLDER / video_name
    print(f"Creating output frames folder: {video_output_folder}")
    video_output_folder.mkdir(parents=True, exist_ok=True)

    # Naming format: <video_file_name>_<time_in_seconds_from_0>_<Nth-frame-in-a-second>.jpg
    output_template = str(video_output_folder / f"{video_name}_%04d.jpg")
    print(f"Output template: {output_template}")

    if hw_accel is "none":
        command = [
            FFMPEG_PATH, "-i", input_path,
            "-vf", f"fps={fps},format=rgb24",
            output_template
        ]
    else:
        command = [
            FFMPEG_PATH, "-hwaccel", hw_accel, "-i", input_path,
            "-vf", f"fps={fps},format=rgb24",
            output_template
        ]
    print(f"Running command: {command}")

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")

    return str(video_output_folder)

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

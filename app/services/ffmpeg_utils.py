import subprocess, json, re
from config import FFMPEG_PATH, FFPROBE_PATH, HW_ACCEL_OPTIONS, OUTPUT_FOLDER
from pathlib import Path

def get_video_info(input_url: str):
    """Retrieve video format, resolution, frame rate, codec, etc. using ffmpeg to decode first frame."""
    # Use ffmpeg to decode just the first frame and get stream info
    if input_url.startswith('rtsp://'):
        command = [
            FFMPEG_PATH, "-rtsp_transport", "tcp", "-i", input_url,
            "-frames:v", "1",  # Decode only 1 frame
            "-f", "null", "-"  # Output to null (discard the frame)
        ]
    else:
        command = [
            FFMPEG_PATH, "-i", input_url,
            "-frames:v", "1",  # Decode only 1 frame
            "-f", "null", "-"  # Output to null (discard the frame)
        ]
    
    try:
        print(f"Running command: {command}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # Parse the ffmpeg output to extract stream information
        output_lines = result.stderr.split('\n')  # ffmpeg info goes to stderr
        
        video_info = {
            "format": "unknown",
            "codec": "unknown",
            "width": "unknown",
            "height": "unknown",
            "fps": 0.0,
            "duration": 0.0
        }
        
        # Parse stream information from ffmpeg output
        for line in output_lines:
            line = line.strip()
            
            # Extract codec information
            if "Stream #0:0: Video:" in line or "Stream #0:" in line and "Video:" in line:
                # Example: Stream #0:0: Video: mpeg4, yuv420p(tv, progressive), 640x480 [SAR 1:1 DAR 4:3], q=2-31, 200 kb/s, 1 fps, 90k tbn
                # Example: Stream #0:0: Video: wrapped_avframe, yuv420p, 640x480 [SAR 1:1 DAR 4:3], 25 fps, 25 tbr, 1200k tbn, 25 tbc
                # Example: Stream #0:0: Video: h264 (H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10), yuv420p, 1920x1080
                parts = line.split(',')
                if len(parts) >= 1:
                    # Extract codec - look for actual codec name, not container formats
                    codec_part = parts[0].split(':')[-1].strip()
                    codec_name = codec_part.split()[0] if codec_part else "unknown"
                    
                    # Filter out container/wrapper formats and get actual codec
                    wrapper_formats = ['wrapped_avframe', 'avframe', 'rawvideo']
                    if codec_name.lower() in wrapper_formats:
                        # Look for codec in parentheses or next parts
                        # Try to find codec name in the line
                        codec_patterns = ['h264', 'h265', 'hevc', 'mpeg4', 'mpeg2', 'vp8', 'vp9', 'av1']
                        found_codec = "unknown"
                        for pattern in codec_patterns:
                            if pattern in line.lower():
                                found_codec = pattern.upper() if pattern in ['h264', 'h265', 'hevc'] else pattern
                                break
                        video_info["codec"] = found_codec if found_codec != "unknown" else codec_name
                    else:
                        video_info["codec"] = codec_name
                    
                    # Extract resolution - look in multiple places
                    resolution_found = False
                    for part in parts:
                        part = part.strip()
                        if 'x' in part and not resolution_found:
                            # Try to extract resolution from this part
                            # Format: "640x480" or "640x480 [SAR 1:1 DAR 4:3]"
                            try:
                                # Extract just the resolution part
                                res_match = part.split()[0]  # Get first token
                                if 'x' in res_match:
                                    width, height = res_match.split('x')
                                    video_info["width"] = int(width)
                                    video_info["height"] = int(height)
                                    resolution_found = True
                            except (ValueError, IndexError):
                                pass
                    
                    # If resolution not found in comma-separated parts, try parsing the whole line
                    if not resolution_found:
                        res_match = re.search(r'(\d+)x(\d+)', line)
                        if res_match:
                            video_info["width"] = int(res_match.group(1))
                            video_info["height"] = int(res_match.group(2))
                    
                    # Extract frame rate
                    for part in parts:
                        if 'fps' in part:
                            try:
                                # Look for pattern like "25 fps" or "25.0 fps"
                                fps_match = re.search(r'(\d+\.?\d*)\s*fps', part)
                                if fps_match:
                                    video_info["fps"] = float(fps_match.group(1))
                                else:
                                    # Fallback: try to get first number
                                    fps_str = part.split()[0]
                                    video_info["fps"] = float(fps_str)
                            except (ValueError, IndexError):
                                pass
                            break
            
            # Extract format information
            elif "Input #0" in line and "from" in line:
                # Example: Input #0, lavfi, from 'testsrc=duration=3600:size=640x480:rate=1':
                if "rtsp" in line.lower():
                    video_info["format"] = "rtsp"
                elif "lavfi" in line:
                    video_info["format"] = "lavfi"
                else:
                    video_info["format"] = "unknown"
        
        print(f"Stream info: {video_info}")
        return video_info
        
    except subprocess.CalledProcessError as e:
        print(f"Error extracting video info: {str(e)}")
        print(f"ffmpeg stderr: {e.stderr}")
        return {"error": f"Failed to get video info: {str(e)}"}
    except Exception as e:
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
    
    # Always include "none" as a fallback option
    for accel in HW_ACCEL_OPTIONS:
        if accel == "none":
            print(f"✅ Using software decoding (none)")
            return "none"
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
    
    # If no hardware acceleration works, fall back to software decoding
    print(f"⚠️ No hardware acceleration available, using software decoding")
    return "none"

def decode_video2frames_in_jpeg(input_path: str, output_path: str, force_format: str = "none", fps: int = 1, camera_id: str = None):
    """Decode video and extract frames as JPEG at specified FPS."""
    hw_accel = get_best_hwaccel(force_format)
    print(f"Transcoding videos to JPEGs using HW mode: {hw_accel}")
    
    # get video info
    print(f"Getting video info from input: {input_path}")
    v_info = get_video_info(input_path)
    print(f"Video format: {v_info["format"]}, codec: {v_info["codec"]}, width: {v_info["width"]}, height: {v_info["height"]}, fps: {v_info["fps"]}")

    # Use camera_id for output folder if provided, otherwise use video name
    if camera_id:
        video_output_folder = OUTPUT_FOLDER / camera_id
        video_name = camera_id
    else:
        # Fallback to original behavior for backward compatibility
        video_name = Path(input_path).stem  # Extract filename without extension
        video_output_folder = OUTPUT_FOLDER / video_name
    
    print(f"Creating output frames folder: {video_output_folder}")
    video_output_folder.mkdir(parents=True, exist_ok=True)

    # Naming format: <video_file_name>_<time_in_seconds_from_0>_<Nth-frame-in-a-second>.jpg
    output_template = str(video_output_folder / f"{video_name}_%04d.jpg")
    print(f"Output template: {output_template}")

    # Build command with RTSP transport support
    if hw_accel == "none":
        if input_path.startswith('rtsp://'):
            command = [
                FFMPEG_PATH, "-rtsp_transport", "tcp", "-i", input_path,
                "-vf", f"fps={fps},format=rgb24",
                output_template
            ]
        else:
            command = [
                FFMPEG_PATH, "-i", input_path,
                "-vf", f"fps={fps},format=rgb24",
                output_template
            ]
    else:
        if input_path.startswith('rtsp://'):
            command = [
                FFMPEG_PATH, "-hwaccel", hw_accel, "-rtsp_transport", "tcp", "-i", input_path,
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
    if input_url.startswith('rtsp://'):
        command = [
            FFMPEG_PATH, "-rtsp_transport", "tcp", "-i", input_url, "-ss", timestamp,
            "-frames:v", "1", output_image
        ]
    else:
        command = [
            FFMPEG_PATH, "-i", input_url, "-ss", timestamp,
            "-frames:v", "1", output_image
        ]
    return subprocess.run(command, capture_output=True, text=True)

def record_clip(input_url: str, start_time: str, duration: str, output_path: str):
    """Record a video clip from a given timestamp and duration"""
    if input_url.startswith('rtsp://'):
        command = [
            FFMPEG_PATH, "-rtsp_transport", "tcp", "-i", input_url, "-ss", start_time,
            "-t", duration, "-c:v", "copy", "-c:a", "copy", output_path
        ]
    else:
        command = [
            FFMPEG_PATH, "-i", input_url, "-ss", start_time,
            "-t", duration, "-c:v", "copy", "-c:a", "copy", output_path
        ]
    return subprocess.run(command, capture_output=True, text=True)

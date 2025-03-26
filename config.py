import os

# FFmpeg executable path
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

# Hardware acceleration (VAAPI / QSV)
HW_ACCEL = os.getenv("HW_ACCEL", "vaapi")  # Options: 'vaapi' or 'qsv'

# Hardware acceleration priority ( CUDA / QSV / VAAPI)
HW_ACCEL_OPTIONS = ["cuda", "qsv", "vaapi"]  # Priority order
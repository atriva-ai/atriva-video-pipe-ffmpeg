from fastapi import APIRouter, UploadFile, File
from app.services.ffmpeg_utils import decode_video, capture_snapshot, record_clip, get_video_info, check_hardware_acceleration
from app.models.schemas import VideoInfoRequest, VideoDecodeRequest, SnapshotRequest, RecordRequest

router = APIRouter()

@router.get("/test/")
def test():
    return {"message": "Testing successful"}

@router.post("/video-info/")
async def video_info(request: VideoInfoRequest):
    info = get_video_info(request.video_url)
    if info["codec"]:
        return {"message": "Video information retrieved", "info": info}
    raise HTTPException(status_code=500, detail="Could not retrieve video information")

@router.get("/hw-accel/")
async def hw_acceleration():
    result = check_hardware_acceleration()
    return {"message": "Hardware acceleration options", "hardware_accelerations": result}

@router.post("/decode/")
async def decode(request: VideoDecodeRequest):
    result = decode_video(request.video_url, request.output_path)
    if result.returncode == 0:
        return {"message": "Decoding successful", "output": request.output_path}
    raise HTTPException(status_code=500, detail=result.stderr)

@router.post("/snapshot/")
async def snapshot(request: SnapshotRequest):
    result = capture_snapshot(request.video_url, request.timestamp, request.output_image)
    if result.returncode == 0:
        return {"message": "Snapshot captured", "output": request.output_image}
    raise HTTPException(status_code=500, detail=result.stderr)

@router.post("/record/")
async def record(request: RecordRequest):
    result = record_clip(request.video_url, request.start_time, request.duration, request.output_path)
    if result.returncode == 0:
        return {"message": "Recording successful", "output": request.output_path}
    raise HTTPException(status_code=500, detail=result.stderr)
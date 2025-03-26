from pydantic import BaseModel

class VideoInfoRequest(BaseModel):
    video_url: str

class VideoDecodeRequest(BaseModel):
    video_url: str
    output_path: str

class SnapshotRequest(BaseModel):
    video_url: str
    timestamp: str
    output_image: str

class RecordRequest(BaseModel):
    video_url: str
    start_time: str
    duration: str
    output_path: str

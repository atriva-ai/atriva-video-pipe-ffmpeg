# Installation Guide

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **Architecture**: x86_64
- **Docker**: 20.10+
- **Docker Compose**: 1.29+ (optional)

### Hardware Requirements

#### Minimum
- CPU: 2 cores
- RAM: 2GB
- Storage: 10GB free space

#### Recommended (for hardware acceleration)
- CPU: 4+ cores
- RAM: 4GB+
- GPU: NVIDIA/Intel with hardware acceleration support
- Storage: 50GB+ for frame storage

### Software Dependencies

- Docker Engine
- NVIDIA Container Toolkit (for CUDA support)
- Intel Media Driver (for QSV/VAAPI support)

## Installation Methods

### Method 1: Docker Build

```bash
# Clone the repository
git clone https://github.com/atriva-ai/video-pipeline-ffmpeg-x86.git
cd video-pipeline-ffmpeg-x86

# Build the Docker image
docker build -t atriva-video-pipeline-x86 .

# Create required directories
mkdir -p frames videos
chmod -R 777 frames videos

# Run the container
docker run -d \
  --name video-pipeline \
  -p 8002:8002 \
  --device /dev/dri:/dev/dri \
  -v $(pwd)/frames:/app/frames \
  -v $(pwd)/videos:/app/videos \
  atriva-video-pipeline-x86
```

### Method 2: Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  video-pipeline:
    build: .
    container_name: atriva-video-pipeline-x86
    ports:
      - "8002:8002"
    volumes:
      - shared-frames:/app/frames
      - video-storage:/app/videos
    devices:
      - /dev/dri:/dev/dri
    environment:
      - FFMPEG_PATH=ffmpeg
      - FFPROBE_PATH=ffprobe
    restart: unless-stopped

volumes:
  shared-frames:
  video-storage:
```

Run with:

```bash
docker-compose up -d
```

## Hardware Acceleration Setup

### NVIDIA CUDA

1. Install NVIDIA drivers:
```bash
sudo apt-get update
sudo apt-get install -y nvidia-driver-470
```

2. Install NVIDIA Container Toolkit:
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

3. Run with CUDA support:
```bash
docker run --runtime=nvidia \
  -e NVIDIA_VISIBLE_DEVICES=all \
  atriva-video-pipeline-x86
```

### Intel QSV/VAAPI

1. Install Intel Media Driver:
```bash
sudo apt-get update
sudo apt-get install -y \
  intel-media-va-driver-non-free \
  vainfo
```

2. Verify VAAPI access:
```bash
vainfo
```

3. Run with device access:
```bash
docker run --device /dev/dri:/dev/dri \
  atriva-video-pipeline-x86
```

## Configuration

### Environment Variables

Set these in your Docker run command or docker-compose.yml:

```bash
FFMPEG_PATH=ffmpeg              # FFmpeg executable path
FFPROBE_PATH=ffprobe            # FFprobe executable path
UPLOAD_FOLDER=/app/videos       # Video upload directory
OUTPUT_FOLDER=/app/frames       # Frame output directory
```

### Volume Mounts

**Required Volumes:**
- `/app/frames` - Frame output (should be shared with AI inference containers)
- `/app/videos` - Video storage (optional, for file uploads)

**Example:**
```bash
-v /host/path/to/frames:/app/frames
-v /host/path/to/videos:/app/videos
```

## Verification

### Check Service Health

```bash
curl http://localhost:8002/api/v1/video-pipeline/health/
```

Expected response:
```json
{
  "status": "healthy",
  "service": "video-pipeline"
}
```

### Check Hardware Acceleration

```bash
curl http://localhost:8002/api/v1/video-pipeline/hw-accel-cap/
```

### Test Video Processing

```bash
curl -X POST "http://localhost:8002/api/v1/video-pipeline/video-info/" \
  -F "video=@test_video.mp4"
```

## Troubleshooting

### Container Won't Start

1. Check Docker logs:
```bash
docker logs video-pipeline
```

2. Verify port availability:
```bash
netstat -tuln | grep 8002
```

### Hardware Acceleration Not Working

1. Verify device access:
```bash
docker exec video-pipeline vainfo  # For VAAPI
docker exec video-pipeline nvidia-smi  # For CUDA
```

2. Check FFmpeg hardware support:
```bash
docker exec video-pipeline ffmpeg -hwaccels
```

### Permission Issues

1. Ensure volume permissions:
```bash
chmod -R 777 /path/to/frames
chmod -R 777 /path/to/videos
```

2. Check container user:
```bash
docker exec video-pipeline whoami
```

### Network Issues

1. Verify container networking:
```bash
docker network ls
docker inspect video-pipeline | grep NetworkMode
```

## Production Deployment

### Security Considerations

1. Use read-only mounts where possible
2. Implement authentication/authorization
3. Use secrets management for sensitive data
4. Enable logging and monitoring

### Resource Limits

Set appropriate resource limits:

```yaml
services:
  video-pipeline:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

### High Availability

- Use container orchestration (Kubernetes, Docker Swarm)
- Implement health checks
- Set up auto-restart policies
- Use load balancers for multiple instances


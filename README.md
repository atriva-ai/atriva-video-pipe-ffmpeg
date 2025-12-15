# Atriva Video Pipeline API Service - FFmpeg x86

## Overview

The **Atriva Video Pipeline API Service** is a containerized microservice that provides FFmpeg-based video processing capabilities for the Atriva AI platform. This service is specifically built for **x86 architectures** and serves as a critical component in the video processing pipeline, decoding video streams and extracting frames for downstream AI inference services.

### Key Purpose

This service acts as a **video decoder and frame extractor** that:
- Receives video input from files or streaming URLs (including RTSP)
- Decodes video streams using hardware-accelerated FFmpeg
- Extracts frames as JPEG images at configurable frame rates
- Stores decoded frames in a **shared volume structure** accessible by AI inference containers
- Provides video metadata and processing status information

### Platform-Specific Note

This implementation targets **x86/x86_64 architectures**. Similar containers may exist for other platforms (ARM, etc.) with platform-specific optimizations.

## Features

- 🚀 **Video Upload & Processing** - Support for file uploads and URL-based video sources
- 🎥 **RTSP Stream Support** - Real-time streaming with auto-reconnection
- ⚡ **Hardware Acceleration** - CUDA, QSV, and VAAPI support for x86 platforms
- 📸 **Frame Extraction** - Extract frames as JPEGs at configurable FPS
- 📊 **Video Metadata** - Retrieve video information and codec details
- 🔄 **Multi-Camera Support** - Concurrent processing for multiple camera streams
- 🐳 **Dockerized** - Containerized for easy deployment and scaling
- 📁 **Shared Storage** - Decoded frames stored in shared volumes for AI inference

## Quick Start

### Prerequisites

- Docker (with support for hardware acceleration if needed)
- NVIDIA/Intel GPU drivers (for hardware acceleration)
- Shared volume mount for frame storage

### Build & Run

```bash
# Build the Docker image
docker build -t atriva-video-pipeline-x86 .

# Run the container
docker run --rm -p 8002:8002 \
  --device /dev/dri:/dev/dri \  # For VAAPI acceleration
  -v /path/to/shared/frames:/app/frames \  # Shared frame storage
  -v /path/to/videos:/app/videos \  # Video storage
  atriva-video-pipeline-x86
```

## Documentation

For detailed documentation, see the [`docs/`](./docs/) directory:

- **[Architecture](./docs/architecture/README.md)** - System architecture and shared storage structure
- **[Installation](./docs/installation/README.md)** - Detailed installation and deployment guide
- **[Development](./docs/development/README.md)** - Development setup and contribution guidelines
- **[Testing](./docs/testing/README.md)** - Testing procedures and examples
- **[Integration](./docs/integration/README.md)** - Integration guide for other services

## API Endpoints

### Core Endpoints

- `POST /api/v1/video-pipeline/decode/` - Start decoding video and extracting frames
- `GET /api/v1/video-pipeline/decode/status/` - Get decoding status for a camera
- `POST /api/v1/video-pipeline/decode/stop/` - Stop decoding for a camera
- `GET /api/v1/video-pipeline/latest-frame/` - Get the latest decoded frame
- `POST /api/v1/video-pipeline/video-info/` - Get video metadata
- `GET /api/v1/video-pipeline/hw-accel-cap/` - Check hardware acceleration capabilities
- `GET /api/v1/video-pipeline/health/` - Health check endpoint

See [Integration Guide](./docs/integration/README.md) for detailed API documentation.

## Shared Frame Storage

Decoded frames are stored in a shared volume structure:

```
/app/frames/
├── {camera_id_1}/
│   ├── frame_0001.jpg
│   ├── frame_0002.jpg
│   └── ...
├── {camera_id_2}/
│   ├── frame_0001.jpg
│   └── ...
└── ...
```

This structure allows AI inference containers to access frames directly from the shared volume without requiring API calls.

## License

MIT License

## Contributing

Pull requests are welcome! Please see the [Development Guide](./docs/development/README.md) for contribution guidelines.

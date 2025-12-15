# Architecture Documentation

## System Architecture

The Video Pipeline service is designed as a microservice within the Atriva platform ecosystem, specifically built for x86 architectures.

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Atriva Platform                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    ┌──────────────────┐                      │
│                    │  Dashboard      │                      │
│                    │  Backend        │                      │
│                    └────────┬─────────┘                      │
│                             │                                │
│                ┌────────────┼────────────┐                  │
│                │            │            │                  │
│                │ HTTP       │ HTTP       │                  │
│                ▼            ▼            │                  │
│      ┌──────────────────┐  ┌──────────────────┐             │
│      │  Video Pipeline  │  │  AI Inference   │             │
│      │  Service (x86)   │  │  Containers      │             │
│      └────────┬─────────┘  │  (YOLO, etc.)    │             │
│               │            └────────┬─────────┘             │
│               │                     │                       │
│               │ Writes              │ Reads                 │
│               │                     │                       │
│               └──────────┬──────────┘                       │
│                          │                                   │
│                          ▼                                   │
│                 ┌──────────────────┐                         │
│                 │  Shared Volume   │                         │
│                 │  /app/frames/    │                         │
│                 │  ├── camera_1/   │                         │
│                 │  └── camera_2/   │                         │
│                 └──────────────────┘                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Shared Storage Architecture

### Purpose

The shared storage volume serves as a **decoupling mechanism** between the video pipeline service and AI inference containers. Both services are orchestrated by the Dashboard Backend and communicate through the shared volume, not directly with each other. This design allows:

- **Decoupled Services**: Video pipeline and AI inference containers operate independently
- **Orchestration**: Dashboard Backend coordinates both services via HTTP/REST APIs
- **High Performance**: Direct filesystem access is faster than API calls for frame data
- **Scalability**: Multiple AI containers can read from the same frames simultaneously
- **Platform Independence**: Different platform-specific video pipeline containers can write to the same structure

### Volume Structure

```
/shared/frames/                    # Shared volume mount point
│
├── {camera_id_1}/                 # Per-camera frame directory
│   ├── frame_0001.jpg            # Sequential frame files
│   ├── frame_0002.jpg
│   ├── frame_0003.jpg
│   └── ...
│
├── {camera_id_2}/
│   ├── frame_0001.jpg
│   └── ...
│
└── ...
```

### Frame Storage Details

- **Format**: JPEG images
- **Naming**: Sequential numbering (`frame_%04d.jpg`)
- **Organization**: One directory per camera ID
- **Access Pattern**: Write-once, read-many (WORM)
- **Cleanup**: Frames are cleaned up when decoding stops or camera is removed

### Multi-Platform Support

This x86 implementation writes frames to the shared volume. Similar containers for other platforms (ARM, etc.) should follow the same structure:

```
Platform-Specific Containers:
├── video-pipeline-ffmpeg-x86/     # This container
├── video-pipeline-ffmpeg-arm/     # ARM variant (future)
└── video-pipeline-ffmpeg-other/   # Other platforms
```

All containers write to the same shared volume structure, ensuring compatibility with AI inference containers regardless of the source platform.

## Data Flow

### 1. Video Input & Orchestration

- **Dashboard Backend** receives video processing requests
- **File Upload**: Video files uploaded to Dashboard Backend
- **URL Input**: HTTP/HTTPS video URLs or RTSP streams
- Dashboard Backend forwards requests to appropriate services

### 2. Video Pipeline Processing

1. **Dashboard Backend** calls Video Pipeline API to start decoding
2. Video Pipeline receives decode request via HTTP/REST
3. FFmpeg decodes video stream
4. Frames extracted at specified FPS
5. Frames saved as JPEG to `/app/frames/{camera_id}/` in shared volume

### 3. AI Inference Processing

1. **Dashboard Backend** calls AI Inference container API to start processing
2. AI Inference containers read frames directly from shared volume (`/app/frames/{camera_id}/`)
3. Containers process frames for inference (object detection, classification, etc.)
4. Results sent back to Dashboard Backend via HTTP/REST API
5. Dashboard Backend aggregates and stores results

### 4. Service Independence

- **No Direct Communication**: Video Pipeline and AI Inference containers do not communicate directly
- **Shared Volume Only**: Both services access the same shared volume independently
- **Orchestration**: Dashboard Backend coordinates the workflow between services

## Hardware Acceleration

### Supported Methods (x86)

1. **CUDA** (NVIDIA GPUs)
2. **QSV** (Intel Quick Sync Video)
3. **VAAPI** (Linux GPU acceleration)
4. **Software** (CPU fallback)

### Selection Priority

The service automatically selects the best available acceleration method based on:
- Hardware availability
- Driver support
- Runtime detection

## Service Communication

### Dashboard Backend to Services

- **Protocol**: HTTP/REST
- **Video Pipeline Port**: 8002 (configurable)
- **AI Inference Port**: Varies by inference service
- **Format**: JSON
- **Direction**: Dashboard Backend → Services (orchestration)
- **Authentication**: TBD (to be implemented)

### Service to Dashboard Backend

- **Protocol**: HTTP/REST
- **Format**: JSON
- **Direction**: Services → Dashboard Backend (results/status)
- **Response**: Processing results, status updates, errors

### Shared Volume Communication

- **Type**: Shared Docker/Kubernetes volume
- **Protocol**: Filesystem
- **Video Pipeline Access**: Write-only (writes frames)
- **AI Inference Access**: Read-only (reads frames)
- **No Direct Service Communication**: Services do not communicate with each other, only through shared volume

## Scalability Considerations

### Horizontal Scaling

- Multiple video pipeline instances can run concurrently
- Each instance handles different camera IDs
- Shared volume accessible by all instances

### Resource Management

- Frame cleanup on decode stop
- Automatic orphaned frame cleanup
- Configurable FPS to balance quality vs. storage

## Security Architecture

### Current State

- No authentication (development)
- File permissions via volume mounts
- Input validation on API endpoints

### Future Enhancements

- JWT token authentication
- Role-based access control
- Encrypted volume mounts
- Audit logging


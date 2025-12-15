# Development Guide

## Development Setup

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/atriva-ai/video-pipeline-ffmpeg-x86.git
cd video-pipeline-ffmpeg-x86
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up local directories:**
```bash
mkdir -p frames videos
```

5. **Run the application:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

## Project Structure

```
video-pipeline-ffmpeg-x86/
├── app/
│   ├── __init__.py
│   ├── routes.py              # API route definitions
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models
│   └── services/
│       ├── __init__.py
│       └── ffmpeg_utils.py    # FFmpeg wrapper functions
├── config.py                  # Configuration settings
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Production Docker image
├── Dockerfile.base            # Base Docker image
├── readme.md                  # Project overview
└── docs/                      # Additional documentation
    ├── architecture/
    ├── installation/
    ├── development/
    ├── integration/           # Integration documentation
    └── testing/
```

## Code Organization

### API Routes (`app/routes.py`)

- Define all API endpoints
- Handle request/response validation
- Manage decode task lifecycle
- Coordinate with FFmpeg services

### FFmpeg Utilities (`app/services/ffmpeg_utils.py`)

- Video information extraction
- Hardware acceleration detection
- Frame extraction logic
- Snapshot and recording functions

### Configuration (`config.py`)

- Path configurations
- Hardware acceleration options
- FFmpeg executable paths

## Development Workflow

### Making Changes

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes
3. Test locally (see Testing section)
4. Commit changes:
```bash
git commit -m "Description of changes"
```

5. Push and create pull request

### Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions focused and small

### Testing

See [Testing Guide](./testing/README.md) for detailed testing procedures.

## Building Docker Images

### Development Build

```bash
docker build -t atriva-video-pipeline-x86:dev .
```

### Production Build

```bash
docker build -t atriva-video-pipeline-x86:latest .
```

### Using Base Image

If you have a custom base image:

```bash
# Build base image first
docker build -f Dockerfile.base -t video-pipeline-base .

# Then build main image
docker build -t atriva-video-pipeline-x86 .
```

## Debugging

### Local Debugging

1. **Enable debug mode:**
```python
# In main.py, uncomment debugpy lines
import debugpy
debugpy.listen(("0.0.0.0", 5678))
```

2. **Attach debugger** from your IDE

### Container Debugging

1. **Access container shell:**
```bash
docker exec -it video-pipeline /bin/bash
```

2. **Check FFmpeg:**
```bash
ffmpeg -version
ffmpeg -hwaccels
```

3. **View logs:**
```bash
docker logs -f video-pipeline
```

### Common Debugging Tasks

- **Check frame output:**
```bash
ls -la /app/frames/camera_1/
```

- **Test FFmpeg command manually:**
```bash
ffmpeg -i input.mp4 -vf "fps=1,format=rgb24" output/frame_%04d.jpg
```

- **Monitor process:**
```bash
ps aux | grep ffmpeg
```

## Adding New Features

### Adding a New API Endpoint

1. Add route in `app/routes.py`:
```python
@router.post("/new-endpoint/")
async def new_endpoint(param: str):
    # Implementation
    return {"message": "success"}
```

2. Update API documentation if needed
3. Add tests

### Adding FFmpeg Functionality

1. Add function in `app/services/ffmpeg_utils.py`:
```python
def new_ffmpeg_function(input_path: str, output_path: str):
    command = [FFMPEG_PATH, "-i", input_path, ...]
    result = subprocess.run(command, ...)
    return result
```

2. Add corresponding API endpoint if needed
3. Test with various inputs

## Platform-Specific Considerations

### x86-Specific Code

This implementation targets x86. When adding features:

- Consider hardware acceleration availability
- Test on x86 hardware
- Document any x86-specific assumptions
- Note if feature could work on other platforms

### Multi-Platform Compatibility

If creating similar containers for other platforms:

- Maintain same API interface
- Use same shared volume structure
- Document platform differences
- Share common patterns where possible

## Performance Optimization

### FFmpeg Optimization

- Use hardware acceleration when available
- Optimize frame extraction FPS based on use case
- Consider frame quality vs. file size trade-offs

### Python Optimization

- Use async/await for I/O operations
- Avoid blocking operations in request handlers
- Consider connection pooling for external services

## Contributing

### Pull Request Process

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Add/update tests
5. Update documentation
6. Submit pull request with description

### Code Review Guidelines

- Ensure code follows style guidelines
- Verify tests pass
- Check documentation is updated
- Confirm no breaking changes (or document them)

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Docker Documentation](https://docs.docker.com/)


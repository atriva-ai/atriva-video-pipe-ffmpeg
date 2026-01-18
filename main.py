from fastapi import FastAPI
from app.routes import router, check_and_restart_decode_processes  # Import API routes and monitoring function
from config import UPLOAD_FOLDER, OUTPUT_FOLDER
import asyncio
# import debugpy

# debugpy.listen(("0.0.0.0", 5678))  # Allow debugger to connect
# print("Waiting for debugger to attach...")
# debugpy.wait_for_client()

# Ensure base folder exists
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Video Pipeline API", version="1.0")

# Include Routes
app.include_router(router)

@app.get("/")
def root():
    return {"message": "FFMPEG Video Pipeline API is running!"}

async def background_monitor_decode_processes():
    """
    Background task that periodically monitors all decode processes
    and restarts any that have stopped. This ensures the decode pipeline
    continues working even when the frontend is not actively viewing cameras.
    """
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            check_and_restart_decode_processes()
        except Exception as e:
            print(f"Error in background monitor: {e}")
            # Continue monitoring even if there's an error
            await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    """Start background monitoring task when the app starts"""
    print("Starting background decode process monitor...")
    asyncio.create_task(background_monitor_decode_processes())
    print("Background monitor started. Decode processes will be automatically restarted if they stop.")

from fastapi import FastAPI
from app.routes import router  # Import API routes

# import debugpy

# debugpy.listen(("0.0.0.0", 5678))  # Allow debugger to connect
# print("Waiting for debugger to attach...")
# debugpy.wait_for_client()

app = FastAPI(title="Video Pipeline API", version="1.0")

# Include Routes
app.include_router(router)

@app.get("/")
def root():
    return {"message": "FFMPEG Video Pipeline API is running!"}

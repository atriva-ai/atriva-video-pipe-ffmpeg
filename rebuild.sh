#!/bin/bash
CONTAINER_NAME="atriva-vpipe"
IMAGE_NAME="atriva-vpipe-ffmpeg"

echo "🛑 Stopping and removing old container..."
docker stop $CONTAINER_NAME 2>/dev/null && docker rm $CONTAINER_NAME 2>/dev/null

echo "🗑️  Removing old image..."
docker rmi $IMAGE_NAME 2>/dev/null

echo "🚀 Rebuilding the Docker image..."
docker build -t $IMAGE_NAME .

echo "🎯 Running the new container..."
docker run -d -p 8000:8000 -p 5678:5678 --name $CONTAINER_NAME $IMAGE_NAME

# echo "🎯 Running the new container from the host folder, must manually install venv..."
# docker run -d -p 8000:8000 -p 5678:5678 -v $(pwd):/app --name $CONTAINER_NAME $IMAGE_NAME

echo "✅ Done!"

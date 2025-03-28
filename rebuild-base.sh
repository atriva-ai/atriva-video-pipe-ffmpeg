#!/bin/bash
IMAGE_NAME="atriva-vpipe-ffmpeg-base"

echo "🛑 Stopping and removing old container..."
docker stop $CONTAINER_NAME 2>/dev/null && docker rm $CONTAINER_NAME 2>/dev/null

echo "🗑️  Removing old image..."
docker rmi $IMAGE_NAME 2>/dev/null

echo "🚀 Rebuilding the Docker image..."
docker build -t $IMAGE_NAME -f Dockerfile.base .

echo "🎯 Running the new base container for development..."
docker run --rm -it -p 8000:8000 -p 5678:5678 -v $(pwd):/app --name $IMAGE_NAME base 

echo "✅ Done!"

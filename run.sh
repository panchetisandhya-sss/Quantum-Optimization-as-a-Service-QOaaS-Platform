#!/bin/bash
echo "=================================================="
echo "Starting Enterprise QOaaS Platform Clean Rebuild..."
echo "=================================================="

# Run rebuild using docker compose (uses cache for packages)
sudo docker compose build

if [ $? -eq 0 ]; then
  echo "=================================================="
  echo "Build Successful! Starting containers..."
  echo "=================================================="
  sudo docker compose up -d
  echo "=================================================="
  echo "QOaaS Platform is running!"
  echo "👉 Frontend Portal: http://localhost:3000"
  echo "👉 Backend Gateway: http://localhost:8000"
  echo "=================================================="
else
  echo "=================================================="
  echo "Error: Docker build failed. Please check logs."
  echo "=================================================="
fi

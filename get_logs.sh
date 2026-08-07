#!/bin/bash
echo "Retrieving Docker container logs for the backend..."
sudo docker compose logs backend > backend_logs.txt
echo "Logs successfully written to backend_logs.txt!"

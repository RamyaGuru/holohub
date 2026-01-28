#!/bin/bash
# Simple NATS server launcher

echo "Starting NATS server on port 4222..."
docker run --network host nats:latest

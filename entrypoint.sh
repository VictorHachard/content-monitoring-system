#!/bin/bash

# Check for required environment variables
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
  echo "Error: DISCORD_WEBHOOK_URL is not set. This variable is required."
  exit 1
fi
if [ -z "RULES" ]; then
  echo "Error: RULES is not set. This variable is required."
  exit 1
fi

# Set the storage directory (volume is defined in Dockerfile)
STORAGE_DIR="/app/data"

# Ensure the storage directory exists
mkdir -p "$STORAGE_DIR"

# Run the application
exec python ./main.py --storage-dir "$STORAGE_DIR" --webhook "$DISCORD_WEBHOOK_URL" --interval "${INTERVAL:-300}" --rules "$RULES"

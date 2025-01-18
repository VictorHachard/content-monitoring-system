#!/bin/bash

# Check for required environment variables
if [ -z "$DISCORD_WEBHOOK_URL" ]; then
  echo "Error: DISCORD_WEBHOOK_URL is not set. This variable is required."
  exit 1
fi
if [ -z "$RULES" ]; then
  echo "Error: RULES is not set. This variable is required."
  exit 1
fi

# Set the storage directory (volume is defined in Dockerfile)
STORAGE_DIR="/app/data"

# Ensure the storage directory exists
mkdir -p "$STORAGE_DIR"

# Build the base command
CMD=("python" "./main.py" "--storage-dir" "$STORAGE_DIR" "--webhook" "$DISCORD_WEBHOOK_URL" "--interval" "${INTERVAL:-300}" "--rules" "$RULES")

# Add --mention_users parameter if MENTION_USERS is set
if [ -n "$MENTION_USERS" ]; then
  CMD+=("--mention-users" "$MENTION_USERS")
fi

# Run the application
"${CMD[@]}"
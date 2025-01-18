# Content Monitoring System Configuration

This repository contains a Docker Compose configuration for the Content Monitoring System.

## Structure

- **Service**:  
  The `content_monitoring_system` uses a prebuilt Docker image hosted on GitHub Container Registry.

- **Docker Image**:  
  - `ghcr.io/VictorHachard/cms:<version>`

- **Environment Variables**:
  - `DISCORD_WEBHOOK_URL`: The Discord webhook URL for notifications. Example:
    ```
    https://discord.com/api/webhooks/1234567890/ABCDEFGHIJKLMNOPQRSTUVWXYZ
    ```
  - `INTERVAL`: Specifies the monitoring interval in seconds. The default value is `300`.
  - `RULES`: A JSON string that configures the selectors for monitored pages. Example configuration:
    ```json
    {
      "https://example.com/page": {
        "selectors": ["div.test-selector"],
        "use_selenium": false
      }
    }
    ```

- **Volumes**:
  - `/app/data`: A volume mounted on the container for persistent storage of monitoring results.

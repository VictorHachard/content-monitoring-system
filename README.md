# Content Monitoring System

This repository provides a Docker Compose setup for the Content Monitoring System, which monitors specified web pages for content changes and sends notifications via Discord webhook.

## Features
- Monitor webpage content using CSS selectors.
- Optionally use Selenium for pages that require full rendering before DOM access.
- Get real-time notifications through Discord webhooks.

## Overview

### Docker Image

  - `ghcr.io/victorhachard/cms:VERSION`

## Configuration

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
    - `selectors`: An array of CSS selectors to monitor.
    - `use_selenium`: A boolean value that specifies whether to use Selenium for monitoring. Selenium is required if the webpage needs to be fully loaded before accessing the DOM. The default value is `false`.

## Volumes

  - `/app/data`: A volume mounted on the container for persistent storage of monitoring results.


## Docker Compose Example

```yaml
services:
  content_monitoring_system:
    image: ghcr.io/victorhachard/cms:VERSION
    environment:
      DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/1234567890/ABCDEFGHIJKLMNOPQRSTUVWXYZ
      INTERVAL: 300
      RULES: |
        {
          "https://example.com/page": {
              "selectors": ["div.test-selector"],
              "use_selenium": false
            }
        }
    volumes:
      - app_data:/app/data

volumes:
  app_data:
```

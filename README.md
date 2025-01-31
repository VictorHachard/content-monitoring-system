# Content Monitoring System

This repository provides a Docker Compose setup for the Content Monitoring System, which monitors specified web pages for content changes and sends notifications via Discord webhook.

## Features

- Monitor webpage content using CSS selectors.
- Monitor API response content using JSON selectors.
- Optionally use Selenium for pages that require full rendering before DOM access.
- Get real-time notifications through Discord webhooks.
- Mention specific users in notifications.

## Overview

### Docker Image

  - `ghcr.io/victorhachard/cms:VERSION`

## Configuration

  - `DISCORD_WEBHOOK_URL`: The Discord webhook URL for notifications. Example:
    ```
    https://discord.com/api/webhooks/1234567890/ABCDEFGHIJKLMNOPQRSTUVWXYZ
    ```
  - `MENTION_USERS`: A comma-separated list of Discord user IDs to mention in notifications. Example:
    ```
    1234567890,0987654321
    ```
  - `WEBPAGE_USER_AGENT`: The user agent string to use for webpage requests. There is a default value.
  - `API_USER_AGENT`: The user agent string to use for API requests. There is a default value.
  - `INTERVAL`: Specifies the monitoring interval in seconds. The default value is `300`.
  - `RULES`: A JSON string that configures the selectors for monitored pages. Example configuration:
    ```json
    {
      "https://example.com/page": {
        "webpage_check": true,
        "notification_on_error": false,
        "selectors": ["div.test-selector"],
        "use_selenium": false
      },
      "https://api.example.com/page": {
        "api_check": true,
        "notification_on_error": false,
        "json_selectors": ["searchedProducts.0.name"]
      }
    }
    ```
    - `webpage_check`: A boolean value that specifies whether to monitor the webpage content.
      - `selectors`: An array of CSS selectors to monitor.
      - `use_selenium`: A boolean value that specifies whether to use Selenium for monitoring. Selenium is required if the webpage needs to be fully loaded before accessing the DOM. The default value is `false`.
    - `api_check`: A boolean value that specifies whether to monitor the API response content.
      - `json_selectors`: An array of JSON selectors to monitor.
    - Both `webpage_check` and `api_check` settings:
      - `notification_on_error`: A boolean value that specifies whether to send a notification when an request error occurs. The default value is `true`.

## Volumes

  - `/app/data`: A volume mounted on the container for persistent storage of monitoring results.

## Docker Compose Example

```yaml
services:
  content_monitoring_system:
    image: ghcr.io/victorhachard/cms:VERSION
    environment:
      DISCORD_WEBHOOK_URL: https://discord.com/api/webhooks/1234567890/ABCDEFGHIJKLMNOPQRSTUVWXYZ
      MENTION_USERS: 1234567890,0987654321
      INTERVAL: 300
      RULES: |
        {
          "https://example.com/page": {
            "webpage_check": true,
            "selectors": ["div.test-selector"],
            "use_selenium": false
          },
          "https://api.example.com/page": {
            "api_check": true,
            "json_selectors": ["searchedProducts.0.name"]
          }
        }
    volumes:
      - app_data:/app/data

volumes:
  app_data:
```

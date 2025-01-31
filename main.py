import time
import logging
import json
import argparse

from configuration_service import ConfigurationService
from vha_toolbox import seconds_to_humantime

from check_version import check_for_update
from checker import check_availability
from notification_service import NotificationService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ],
)


def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Content Monitoring System")
    parser.add_argument('--storage-dir', type=str, required=True, help="Path to directory containing storage data.")
    parser.add_argument('--webhook', type=str, required=True, help="Discord webhook URL.")
    parser.add_argument('--mention-users', type=str, help="Comma-separated list of Discord user IDs to ping.")
    parser.add_argument('--interval', type=int, default=300, help="Interval between checks in seconds.")
    parser.add_argument('--rules', type=str, required=True, help="JSON string defining the rules for availability checks.")

    parser.add_argument(
        '--webpage-user-agent',
        type=str,
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        help="User agent to use for webpage checks."
    )
    #parser.add_argument(
    #    '--webpage-selenium-user-agent',
    #    type=str,
    #    default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    #    help="User agent to use for webpage checks with Selenium."
    #)
    parser.add_argument(
        '--api-user-agent',
        type=str,
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        help="User agent to use for API checks."
    )

    parser.add_argument('--webpage-timeout', type=int, default=5, help="Timeout for webpage checks in seconds.")
    parser.add_argument('--api-timeout', type=int, default=5, help="Timeout for API checks in seconds.")

    return parser.parse_args()


def create_notification_service(webhook_url, mention_users, current_version):
    if current_version:
        footer = f"Content monitoring system {current_version}"
    else:
        footer = "Content monitoring system"
    return NotificationService(webhook_url, mention_users, footer=footer)


if __name__ == "__main__":
    logging.info("Starting Content Monitoring System")
    update = check_for_update()
    
    args = parse_arguments()
    config_service = ConfigurationService()
    config_service.load_from_parser(args)

    interval = config_service.get_config("interval")
    rules = config_service.get_config("rules")
    discord_webhook_url = config_service.get_config("discord_webhook_url")
    mention_users = config_service.get_config("mention_users")

    current_version = update if isinstance(update, str) else update[0] if isinstance(update, tuple) else None
    config_service.set_config("notification_service", create_notification_service(discord_webhook_url, mention_users, current_version))
    notif = config_service.get_config("notification_service")

    rules_formatted = "\n".join(
        f"- **URL**: {url}\n"
        + (f"  - **JSON Selectors**:\n" + "\n".join(f"    - {sel}" for sel in rule['json_selectors']) + "\n" 
        if rule.get("api_check") else "")
        + (f"  - **Selectors**:\n" + "\n".join(f"    - {sel}" for sel in rule['selectors']) + "\n" 
        if rule.get("webpage_check") else "")
        for url, rule in rules.items()
    )
    notif.send(
        title="Content Monitoring System Started",
        description="The content monitoring system has started successfully.",
        fields={"Interval": seconds_to_humantime(interval), "Rules": rules_formatted},
        color='#0dcaf0',
    )
    if isinstance(update, tuple):
        notif.send(
            title="New Version Available",
            description="A new version of the content monitoring system is available. Please update.",
            fields={"Current Version": update[0], "Latest Version": update[1]},
            color='#ffc107',
        )
    del rules_formatted, update, current_version
    logging.info(f"Starting checks with interval of {interval} seconds")
    while True:
        check_availability()
        time.sleep(interval)

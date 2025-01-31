import time
import logging
import json
import os
import argparse
from datetime import datetime, timedelta

from configuration_service import ConfigurationService
from vha_toolbox import seconds_to_humantime

from check_version import check_for_update
from checker import check_availability
from notification_service import NotificationService, NotificationManager

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


def save_data(file_path, data):
    """Saves a dictionary as JSON into the given file path."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def load_data(file_path):
    """Loads a JSON file and returns a dictionary. Returns an empty dict if the file does not exist."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}


def has_notification_been_sent(storage_dir, today):
    """Checks whether today's daily notification has already been sent."""
    status_file = f"{storage_dir}/daily_notification_status.json"
    status_data = load_data(status_file)
    return status_data.get(today, False)


def update_notification_status(storage_dir, today, status=True):
    """Records in a file that today's notification has been sent."""
    status_file = f"{storage_dir}/daily_notification_status.json"
    status_data = load_data(status_file)
    status_data[today] = status
    save_data(status_file, status_data)


def send_daily_discord_notification(config_service):
    """
    Sends a Discord notification summarizing yesterday's monitoring results 
    if it hasn't been sent yet. Expects the daily log file to be stored as 'daily_log.json'
    in the storage directory.
    """
    storage_dir = config_service.get_config("storage_dir")
    log_file = f"{storage_dir}/daily_log.json"
    daily_log = load_data(log_file)
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    if has_notification_been_sent(storage_dir, yesterday):
        logging.info(f"Daily notification for {yesterday} has already been sent.")
        return

    summary = daily_log.get(yesterday, {})
    if summary:
        message_lines = [f"Daily Summary for {yesterday}"]
        for url, counts in summary.items():
            message_lines.append(f"- **URL**: {url}")
            message_lines.append(f"  - Success: `{counts.get('success', 0)}`")
            message_lines.append(f"  - Fail: `{counts.get('fail', 0)}`")
        message = "\n".join(message_lines)

        notif_manager = config_service.get_config("notification_manager")
        notif_manager.send("daily_summary", fields={"Date": yesterday, "Summary": message})
        logging.info(f"Daily notification sent for {yesterday}")
    update_notification_status(storage_dir, yesterday, status=True)


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

    config_service.set_config("notification_manager", NotificationManager(notif))
    notif_manager = config_service.get_config("notification_manager")

    rules_formatted = "\n".join(
        f"- **URL**: {url}\n"
        + (f"  - **JSON Selectors**:\n" + "\n".join(f"    - {sel}" for sel in rule['json_selectors']) + "\n" 
        if rule.get("api_check") else "")
        + (f"  - **Selectors**:\n" + "\n".join(f"    - {sel}" for sel in rule['selectors']) + "\n" 
        if rule.get("webpage_check") else "")
        for url, rule in rules.items()
    )
    notif_manager.send("system_start", fields={"Interval": seconds_to_humantime(interval), "Rules": rules_formatted})
    if isinstance(update, tuple):
        notif_manager.send("update_available", fields={"Current Version": update[0], "Latest Version": update[1]},)
    del rules_formatted, update, current_version
    logging.info(f"Starting checks with interval of {interval} seconds")
    
    while True:
        check_availability()
        now = datetime.now()
        if now.hour == 0 and now.minute < 60:
            send_daily_discord_notification(config_service)
        time.sleep(interval)

import time
import logging
import json

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


if __name__ == "__main__":
    logging.info("Starting Content Monitoring System")
    update = check_for_update()
    import argparse

    parser = argparse.ArgumentParser(description="Content Monitoring System")
    parser.add_argument('--storage-dir', type=str, required=True, help="Path to directory containing storage data.")
    parser.add_argument('--webhook', type=str, required=True, help="Discord webhook URL.")
    parser.add_argument('--mention-users', type=str, help="Comma-separated list of Discord user IDs to ping.")
    parser.add_argument('--interval', type=int, default=300, help="Interval between checks in seconds.")
    parser.add_argument('--rules', type=str, required=True, help="JSON string defining the rules for availability checks.")

    args = parser.parse_args()

    storage_dir = args.storage_dir
    discord_webhook_url = args.webhook
    mention_users = args.mention_users.split(",") if args.mention_users else None
    interval = args.interval

    # Parse rules JSON
    try:
        rules = json.loads(args.rules)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode rules from arguments: {e}")
        rules = {}

    if not rules:
        logging.error("No rules defined. Exiting.")
        exit(1)
    elif interval < 5:
        logging.error("Interval cannot be less than 10 seconds. Exiting.")
        exit(1)
    else:
        current_version = update if isinstance(update, str) else update[0] if isinstance(update, tuple) else None
        if current_version:
            footer = f"Content monitoring system {current_version}"
        else:
            footer = "Content monitoring system"
        notif = NotificationService(discord_webhook_url, mention_users, footer=footer)
        rules_formatted = "\n".join(
            f"- **URL**: {url}\n  - **Selectors**: {', '.join(rule['selectors'])}\n  - **Use Selenium**: {'Yes' if rule['use_selenium'] else 'No'}"
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
        del rules_formatted, update, current_version, footer
        logging.info(f"Starting checks with interval of {interval} seconds")
        while True:
            check_availability(storage_dir, notif, rules)
            time.sleep(interval)

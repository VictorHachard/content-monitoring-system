import time
import logging
import json
from checker import check_availability
from notifications import send_discord_notification

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ],
)


if __name__ == "__main__":
    logging.info("Starting Content Monitoring System")
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
    elif interval < 10:
        logging.error("Interval cannot be less than 10 seconds. Exiting.")
        exit(1)
    else:
        logging.info(f"Starting checks with interval of {interval} seconds.")
        rules_formatted = "\n".join(
            f"- **URL**: {url}\n  - **Selectors**: {', '.join(rule['selectors'])}\n  - **Use Selenium**: {'Yes' if rule['use_selenium'] else 'No'}"
            for url, rule in rules.items()
        )
        send_discord_notification(
            discord_webhook_url,
            title="Content Monitoring System Started",
            description="The content monitoring system has started successfully.",
            fields={"Interval": f"{interval} seconds", "Rules": rules_formatted},
            color='#0dcaf0',
            mention_users=mention_users
        )
        del rules_formatted
        while True:
            check_availability(storage_dir, discord_webhook_url, mention_users, rules)
            time.sleep(interval)

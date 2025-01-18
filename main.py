import time
import logging
import json
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
    def format_interval(interval):
        """
        Formats a time interval (in seconds) into a human-readable string with correct singular/plural forms.
        """
        interval_modified = interval
        interval_formatted = []

        if interval_modified >= 86400:
            days = interval_modified // 86400
            interval_formatted.append(f"{days} day" + ("s" if days > 1 else ""))
            interval_modified %= 86400
        if interval_modified >= 3600:
            hours = interval_modified // 3600
            interval_formatted.append(f"{hours} hour" + ("s" if hours > 1 else ""))
            interval_modified %= 3600
        if interval_modified >= 60:
            minutes = interval_modified // 60
            interval_formatted.append(f"{minutes} minute" + ("s" if minutes > 1 else ""))
            interval_modified %= 60
        if interval_modified > 0:
            interval_formatted.append(f"{interval_modified} second" + ("s" if interval_modified > 1 else ""))

        if len(interval_formatted) > 1:
            return ", ".join(interval_formatted[:-1]) + " and " + interval_formatted[-1]
        elif interval_formatted:
            return interval_formatted[0]
        else:
            return "0 seconds"
        
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
        notif = NotificationService(discord_webhook_url, mention_users)
        rules_formatted = "\n".join(
            f"- **URL**: {url}\n  - **Selectors**: {', '.join(rule['selectors'])}\n  - **Use Selenium**: {'Yes' if rule['use_selenium'] else 'No'}"
            for url, rule in rules.items()
        )
        notif.send(
            title="Content Monitoring System Started",
            description="The content monitoring system has started successfully.",
            fields={"Interval": format_interval(interval), "Rules": rules_formatted},
            color='#0dcaf0',
        )
        del rules_formatted
        while True:
            check_availability(storage_dir, dnotif, rules)
            time.sleep(interval)

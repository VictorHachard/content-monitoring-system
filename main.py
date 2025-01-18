import time
import logging
import json
from checker import check_availability

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ],
)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check availability of items on websites.")
    parser.add_argument('--storage-dir', type=str, required=True, help="Path to directory containing storage data.")
    parser.add_argument('--webhook', type=str, required=True, help="Discord webhook URL.")
    parser.add_argument('--interval', type=int, default=300, help="Interval between checks in seconds.")
    parser.add_argument('--rules', type=str, required=True, help="JSON string defining the rules for availability checks.")

    args = parser.parse_args()

    storage_dir = args.storage_dir
    discord_webhook_url = args.webhook
    interval = args.interval

    # Parse rules JSON
    try:
        rules = json.loads(args.rules)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode rules from arguments: {e}")
        rules = {}

    if not rules:
        logging.warning("No rules defined. Exiting.")
        exit(1)
    else:
        while True:
            check_availability(storage_dir, discord_webhook_url, rules)
            time.sleep(interval)

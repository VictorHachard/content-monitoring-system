import os
import json
import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from json_path_error import JSONPathError
from selenium_session import SeleniumSession


def save_data(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}


def check_availability(storage_dir, notif, rules):
    selenium_session = SeleniumSession() if any(rule.get("use_selenium", False) for rule in rules.values()) else None

    previous_data_path = os.path.join(storage_dir, 'previous_data.json')
    missing_data_path = os.path.join(storage_dir, 'missing_elements.json')

    for url, rule in rules.items():
        previous_data = load_data(previous_data_path)
        if rule.get("api_check"):
            check_api_availability(url, rule, previous_data, notif, previous_data_path)
        elif rule.get("webpage_check"):
            missing_data = load_data(missing_data_path)
            check_webpage_availability(url, rule, selenium_session, previous_data, missing_data, notif, previous_data_path, missing_data_path)


def check_webpage_availability(url, rule, selenium_session, previous_data, missing_data, notif, previous_data_path, missing_data_path):
    current_data = previous_data.copy()
    selectors = rule.get("selectors", [])
    use_selenium = rule.get("use_selenium", False)

    try:
        page_content = fetch_page_content(url, use_selenium, selenium_session)
        soup = BeautifulSoup(page_content, 'html.parser')

        for selector in selectors:
            element = soup.select_one(selector)
            key = f"{url}:{selector}"

            if element is None:
                logging.warning(f"Element missing for {url} with selector {selector}")
                if key not in missing_data or not missing_data[key].get("alert_sent", False):
                    missing_data[key] = {"url": url, "selector": selector, "timestamp": time.time(), "alert_sent": True}
                    save_data(missing_data_path, missing_data)
                    notif.send(
                        title="Element Missing Alert",
                        description=f"The element specified by the selector `{selector}` is missing on the page.",
                        url=url,
                        fields={"URL": url, "Selector": f"`{selector}`"},
                        color='#ffc107',
                    )
                continue

            html_content = element.prettify()
            text_content = element.get_text(strip=True)

            current_data[key] = {"html": html_content, "text": text_content, "timestamp": time.time()}

            if key in missing_data:
                logging.info(f"Element returned for {url} with selector {selector}")
                del missing_data[key]
                save_data(missing_data_path, missing_data)
                notif.send(
                    title="Element Returned Notification",
                    description=f"The element specified by the selector `{selector}` has returned to the page.",
                    url=url,
                    fields={"URL": url, "Selector": f"`{selector}`"},
                    color='#ffc107',
                )

            if key not in previous_data:
                logging.info(f"First-time change detected for {url} with selector {selector}")
                notif.send(
                    title="First-Time Webpage Content Detected",
                    description="Tracking webpage content for the first time.",
                    url=url,
                    fields={
                        "URL": url,
                        "Selector": f"`{selector}`",
                        "Data": f"`{text_content}`",
                    },
                    color='#0dcaf0',
                )
            elif previous_data[key]["html"] != html_content:
                logging.info(f"Change detected for {url} with selector {selector}")
                if 'timestamp' in previous_data[key]:
                    last_updated = datetime.fromtimestamp(previous_data[key]['timestamp'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + ' UTC'
                else:
                    last_updated = "N/A"
                notif.send(
                    title="Webpage Content Change Detected",
                    description="A change was detected on the webpage.",
                    url=url,
                    fields={
                        "URL": url,
                        "Selector": f"`{selector}`",
                        "Old Data": f"`{previous_data[key]['text']}`" if previous_data[key]['text'] else "N/A",
                        "New Data": f"`{text_content}`",
                        "Last Updated": last_updated,
                    },
                    color='#0d6efd',
                )
            else:
                logging.info(f"No change detected for {url} with selector {selector}")
        
        save_data(previous_data_path, current_data)

    except Exception as e:
        logging.error(f"Error checking {url}: {e}")
        notif.send(
            title="Webpage Check Failed",
            description=f"An error occurred while checking {url}.",
            fields={"Exception": f"`{e}`"},
            url=url,
            color='#dc3545'
        )


def check_api_availability(api_url, rule, previous_data, notif, previous_data_path):
    """Fetch product data from the NVIDIA API and compare with previous results."""
    current_data = previous_data.copy()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()

        if not data:
            logging.warning(f"No data found for {api_url}")
            return
        
        json_selectors = rule.get("json_selectors", [])
        extracted_data = {selector: extract_json_value(data, selector) for selector in json_selectors}

        current_data[api_url] = {"json": extracted_data, "timestamp": time.time()}

        for selector, new_value in extracted_data.items():
            key = f"{api_url}:{selector}"
            old_value = previous_data.get(api_url, {}).get("json", {}).get(selector)

            if old_value is None:
                logging.info(f"First-time API tracking for {api_url} selector `{selector}`")
                notif.send(
                    title="First-Time API Content Detected",
                    description=f"Tracking `{selector}` for the first time.",
                    fields={
                        "URL": api_url,
                        "Selector": selector,
                        "Value": str(new_value)
                    },
                    color='#0dcaf0'
                )
            elif old_value != new_value:
                logging.info(f"API data changed for {api_url} selector `{selector}`")
                if 'timestamp' in previous_data[key]:
                    last_updated = datetime.fromtimestamp(previous_data[key]['timestamp'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + ' UTC'
                else:
                    last_updated = "N/A"
                notif.send(
                    title="API Content Change Detected",
                    description="A change was detected on the API.",
                    fields={
                        "URL": api_url,
                        "Selector": selector,
                        "Old Value": str(old_value),
                        "New Value": str(new_value),
                        "Last Updated": last_updated,
                    },
                    color='#0d6efd'
                )
            else:
                logging.info(f"No change detected for {api_url} with selector `{selector}`")
        
        save_data(previous_data_path, current_data)

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching API data from {api_url}: {e}")
        notif.send(
            title="API Check Failed",
            description="Error fetching API data.",
            fields={"URL": api_url, "Exception": f"`{e}`"},
            color='#dc3545'
        )


def extract_json_value(json_data, path):
    """Extracts a value from a nested JSON object using dot notation (e.g., 'searchedProducts.productDetails.0.productPrice')."""
    keys = path.split(".")
    value = json_data
    try:
        for key in keys:
            if key.isdigit():
                key = int(key)
            value = value[key]
        return value
    except (KeyError, IndexError, TypeError) as e:
        raise JSONPathError(path, f"Invalid JSON path at {str(e)}")


def fetch_page_content(url, use_selenium=False, selenium_session=None):
    if use_selenium and selenium_session:
        return selenium_session.fetch_page(url)
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.text
    
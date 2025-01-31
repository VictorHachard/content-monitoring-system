import os
import json
import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
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
    previous_data = load_data(previous_data_path)
    missing_data = load_data(missing_data_path)
    current_data = {}

    for url, rule in rules.items():
        if rule.get("api_check"):
            check_api_availability(url, rule, previous_data, current_data, notif)
        elif rule.get("webpage_check"):
            check_webpage_availability(url, rule, selenium_session, previous_data, current_data, missing_data, notif)

    save_data(previous_data_path, current_data)
    save_data(missing_data_path, missing_data)


def check_webpage_availability(url, rule, selenium_session, previous_data, current_data, missing_data, notif):
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
                if key not in missing_data:
                    missing_data[key] = {"url": url, "selector": selector, "timestamp": time.time()}
                    notif.send(
                        title="Element Missing Alert",
                        description=f"The element `{selector}` is missing.",
                        url=url,
                        fields={"URL": url, "Selector": selector},
                        color='#ffc107'
                    )
                continue

            text_content = element.get_text(strip=True)
            current_data[key] = {"text": text_content, "timestamp": time.time()}

            if key not in previous_data or previous_data[key]["text"] != text_content:
                logging.info(f"Change detected for {url} with selector {selector}")
                notif.send(
                    title="Webpage Content Change Detected",
                    description="A change was detected on the webpage.",
                    url=url,
                    fields={
                        "URL": url,
                        "Selector": selector,
                        "Old Data": previous_data.get(key, {}).get("text", "N/A"),
                        "New Data": text_content
                    },
                    color='#0d6efd'
                )

    except Exception as e:
        logging.error(f"Error checking {url}: {e}")
        notif.send(
            title="Webpage Check Failed",
            description=f"An error occurred while checking {url}.",
            fields={"Exception": str(e)},
            url=url,
            color='#dc3545'
        )


def check_api_availability(api_url, rule, previous_data, current_data, notif):
    """Fetch product data from the NVIDIA API and compare with previous results."""
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

        # Store current API data
        current_data[api_url] = {"json": extracted_data, "timestamp": time.time()}

        for selector, new_value in extracted_data.items():
            key = f"{api_url}:{selector}"
            old_value = previous_data.get(api_url, {}).get("json", {}).get(selector)

            if old_value is None:
                logging.info(f"First-time API tracking for {api_url} selector `{selector}`")
                notif.send(
                    title="First-Time API Content Detected",
                    description=f"Tracking `{selector}` for the first time.",
                    fields={"URL": api_url, "Selector": selector, "Value": str(new_value)},
                    color='#0dcaf0'
                )
            elif old_value != new_value:
                logging.info(f"API data changed for {api_url} selector `{selector}`")
                notif.send(
                    title="API Content Change Detected",
                    description=f"Detected change in `{selector}`.",
                    fields={
                        "URL": api_url,
                        "Selector": selector,
                        "Old Value": str(old_value),
                        "New Value": str(new_value)
                    },
                    color='#0d6efd'
                )

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching API data from {api_url}: {e}")
        notif.send(
            title="API Check Failed",
            description="Error fetching API data.",
            fields={"URL": api_url, "Exception": str(e)},
            color='#dc3545'
        )


def extract_json_value(json_data, path):
    """Extracts a value from a nested JSON object using dot notation (e.g., 'searchedProducts.productDetails.0.productPrice')."""
    keys = path.split(".")
    value = json_data
    try:
        for key in keys:
            if key.isdigit():
                key = int(key)  # Convert to integer for list indexing
            value = value[key]
        return value
    except (KeyError, IndexError, TypeError):
        return None  # Return None if path is invalid


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
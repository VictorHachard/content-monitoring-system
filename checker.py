import os
import json
import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from configuration_service import ConfigurationService
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


def update_daily_log_by_url(url, success=0, fail=0):
    """
    Updates (or creates) a daily log file that tracks the number of successful and failed checks by URL.
    """
    config_service = ConfigurationService()
    storage_dir = config_service.get_config("storage_dir")
    log_file = os.path.join(storage_dir, 'daily_log.json')
    daily_log = load_data(log_file)
    today = datetime.now().strftime('%Y-%m-%d')
    
    if today not in daily_log:
        daily_log[today] = {}
    
    if url not in daily_log[today]:
        daily_log[today][url] = {"success": 0, "fail": 0}
    
    daily_log[today][url]["success"] += success
    daily_log[today][url]["fail"] += fail
    
    save_data(log_file, daily_log)


def check_availability():
    config_service = ConfigurationService()
    storage_dir = config_service.get_config("storage_dir")
    rules = config_service.get_config("rules")
    notif = config_service.get_config("notification_service")
    selenium_session = SeleniumSession() if any(rule.get("use_selenium", False) for rule in rules.values()) else None

    previous_data_path = os.path.join(storage_dir, 'previous_data.json')
    missing_data_path = os.path.join(storage_dir, 'missing_elements.json')

    for url, rule in rules.items():
        previous_data = load_data(previous_data_path)
        if rule.get("api_check", False):
            check_api_availability(url, rule, previous_data, notif, previous_data_path)
        elif rule.get("webpage_check", False):
            missing_data = load_data(missing_data_path)
            check_webpage_availability(url, rule, selenium_session, previous_data, missing_data, notif, previous_data_path, missing_data_path)


def check_webpage_availability(url, rule, selenium_session, previous_data, missing_data, notif, previous_data_path, missing_data_path):
    """
    Check the availability of a webpage and compare the HTML content with the previous data.
    """
    current_data = previous_data.copy()
    configuration_service = ConfigurationService()
    notification_manager = configuration_service.get_config("notification_manager")
    selectors = rule.get("selectors", [])
    use_selenium = rule.get("use_selenium", False)

    try:
        if use_selenium and selenium_session:
            page_content = selenium_session.fetch_page(url)
        else:
            headers = {
                "User-Agent": configuration_service.get_config("webpage_user_agent")
            }
            response = requests.get(url, headers=headers, timeout=configuration_service.get_config("webpage_timeout"))
            response.raise_for_status()
            page_content = response.text
    
        soup = BeautifulSoup(page_content, 'html.parser')

        for selector in selectors:
            element = soup.select_one(selector)
            key = f"{url}:{selector}"

            if element is None:
                logging.warning(f"Element missing for {url} with selector {selector}")
                if key not in missing_data or not missing_data[key].get("alert_sent", False):
                    missing_data[key] = {"url": url, "selector": selector, "timestamp": time.time(), "alert_sent": True}
                    save_data(missing_data_path, missing_data)
                    notification_manager.send("element_missing", url=url, fields={"URL": url, "Selector": f"`{selector}`"})
                continue

            html_content = element.prettify()
            text_content = element.get_text(strip=True)

            current_data[key] = {"html": html_content, "text": text_content, "timestamp": time.time()}

            if key in missing_data:
                logging.info(f"Element returned for {url} with selector {selector}")
                del missing_data[key]
                save_data(missing_data_path, missing_data)
                notification_manager.send("element_returned", url=url, fields={"URL": url, "Selector": f"`{selector}`"})

            if key not in previous_data:
                logging.info(f"First-time change detected for {url} with selector {selector}")
                notification_manager.send("first_time_webpage", url=url, fields={
                    "URL": url,
                    "Selector": f"`{selector}`",
                    "Data": f"`{text_content}`",
                })
            elif previous_data[key]["html"] != html_content:
                logging.info(f"Change detected for {url} with selector {selector}")
                if 'timestamp' in previous_data[key]:
                    last_updated = datetime.fromtimestamp(previous_data[key]['timestamp'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + ' UTC'
                else:
                    last_updated = "N/A"
                notification_manager.send("content_change", url=url, fields={
                    "URL": url,
                    "Selector": f"`{selector}`",
                    "Old Data": f"`{previous_data[key]['text']}`" if previous_data[key]['text'] else "N/A",
                    "New Data": f"`{text_content}`",
                    "Last Updated": last_updated,
                })
            else:
                logging.info(f"No change detected for {url} with selector {selector}")
        
        save_data(previous_data_path, current_data)
        update_daily_log_by_url(url, success=1)

    except Exception as e:
        logging.error(f"Error fetching webpage content from {url}: {e}")
        update_daily_log_by_url(url, fail=1)
        if not isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or \
            (
                isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout)) and rule.get("notification_on_error", True)
            ):
            notification_manager.send("webpage_check_failed", url=url, fields={"URL": url, "Exception": f"`{e}`"})


def check_api_availability(api_url, rule, previous_data, notif, previous_data_path):
    """
    Check the availability of an API endpoint and compare the JSON data with the previous data.
    """
    current_data = previous_data.copy()
    configuration_service = ConfigurationService()
    notification_manager = configuration_service.get_config("notification_manager")
    headers = {
        "User-Agent": configuration_service.get_config("api_user_agent"),
        "Accept": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers, timeout=configuration_service.get_config("api_timeout"))
        response.raise_for_status()
        data = response.json()

        if not data:
            logging.warning(f"No data found for {api_url}")
            update_daily_log_by_url(api_url, success=1)
            return
        
        json_selectors = rule.get("json_selectors", [])
        extracted_data = {selector: extract_json_value(data, selector) for selector in json_selectors}

        current_data[api_url] = {"json": extracted_data, "timestamp": time.time()}

        for selector, new_value in extracted_data.items():
            key = f"{api_url}:{selector}"
            old_value = previous_data.get(api_url, {}).get("json", {}).get(selector)

            if old_value is None:
                logging.info(f"First-time API tracking for {api_url} selector `{selector}`")
                notification_manager.send("first_time_api", url=api_url, fields={
                    "URL": api_url,
                    "Selector": f"`{selector}`",
                    "Value": f"`{new_value}`",
                })
            elif old_value != new_value:
                logging.info(f"API data changed for {api_url} selector `{selector}`")
                if 'timestamp' in previous_data[key]:
                    last_updated = datetime.fromtimestamp(previous_data[key]['timestamp'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S') + ' UTC'
                else:
                    last_updated = "N/A"
                notification_manager.send("api_content_change", url=api_url, fields={
                    "URL": api_url,
                    "Selector": f"`{selector}`",
                    "Old Value": f"`{old_value}`",
                    "New Value": f"`{new_value}`",
                    "Last Updated": last_updated
                })
            else:
                logging.info(f"No change detected for {api_url} with selector `{selector}`")
        
        save_data(previous_data_path, current_data)
        update_daily_log_by_url(api_url, success=1)

    except Exception as e:
        logging.error(f"Error fetching API data from {api_url}: {e}")
        update_daily_log_by_url(api_url, fail=1)
        if not isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or \
            (
                isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout)) and rule.get("notification_on_error", True)
            ):
            notification_manager.send("api_check_failed", url=api_url, fields={"URL": api_url, "Exception": f"`{e}`"})


def extract_json_value(json_data, path):
    """
    Extracts a value from a nested JSON object using dot notation
    (e.g., 'searchedProducts.productDetails.0.productPrice').
    """
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

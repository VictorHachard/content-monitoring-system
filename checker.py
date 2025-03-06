import logging
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup
from json_path_error import JSONPathError
from services import ConfigurationService, SeleniumSession


def update_daily_log_by_url(url, success=0, fail=0):
    """
    Updates (or creates) a daily log file that tracks the number of successful and failed checks by URL.
    """
    config_service = ConfigurationService()
    file_service = config_service.get_config("file_service")
    daily_log = file_service.load_json('daily_log.json')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if today not in daily_log:
        daily_log[today] = {}
    
    if url not in daily_log[today]:
        daily_log[today][url] = {"success": 0, "fail": 0}
    
    daily_log[today][url]["success"] += success
    daily_log[today][url]["fail"] += fail

    file_service.save_json('daily_log.json', daily_log)


def check_availability():
    config_service = ConfigurationService()
    rules = config_service.get_config("rules")
    selenium_session = SeleniumSession() if any(rule.get("use_selenium", False) for rule in rules.values()) else None

    for url, rule in rules.items():
        if rule.get("api_check", False):
            check_api_availability(url, rule)
        elif rule.get("webpage_check", False):
            check_webpage_availability(url, rule, selenium_session)


def check_webpage_availability(url, rule, selenium_session):
    """
    Check the availability of a webpage and compare the HTML content with the previous data.
    """
    configuration_service = ConfigurationService()
    notification_manager = configuration_service.get_config("notification_manager")
    file_service = configuration_service.get_config("file_service")
    missing_data = file_service.load_json('missing_data.json')
    previous_data = file_service.load_json('previous_data.json')
    current_data = previous_data.copy()
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
                    file_service.save_json('missing_data.json', missing_data)
                    notification_manager.send("element_missing", url=url, fields={"URL": url, "Selector": f"`{selector}`"})
                continue

            html_content = element.prettify()
            text_content = element.get_text(strip=True)

            current_data[key] = {"html": html_content, "text": text_content, "timestamp": time.time()}

            if key in missing_data:
                logging.info(f"Element returned for {url} with selector {selector}")
                del missing_data[key]
                file_service.save_json('missing_data.json', missing_data)
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
        
        file_service.save_json('missing_data.json', missing_data)
        update_daily_log_by_url(url, success=1)

    except Exception as e:
        logging.error(f"Error fetching webpage content from {url}: {e}")
        update_daily_log_by_url(url, fail=1)
        if not isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or \
            (
                isinstance(e, (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout)) and rule.get("notification_on_error", True)
            ):
            notification_manager.send("webpage_check_failed", url=url, fields={"URL": url, "Exception": f"`{e}`"})


def check_api_availability(api_url, rule):
    """
    Check the availability of an API endpoint and compare the JSON data with the previous data.
    """
    configuration_service = ConfigurationService()
    notification_manager = configuration_service.get_config("notification_manager")
    file_service = configuration_service.get_config("file_service")
    previous_data = file_service.load_json('previous_data.json')
    current_data = previous_data.copy()
    headers = {
        "User-Agent": configuration_service.get_config("api_user_agent"),
        "Accept": "application/json"
    }

    try:
        response = requests.get(
            api_url,
            headers=headers,
            timeout=configuration_service.get_config("api_timeout"),
            proxies=configuration_service.get_config("socks5_proxy", {})
        )
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
        
        file_service.save_json('previous_data.json', current_data)
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
    Extracts a value from a nested JSON object using dot notation.
    Supports the placeholder '<x>' to iterate over a list.
    
    For example, 'days.<x>.day' will extract the 'day' attribute from every item in the 'days' list.
    Raises JSONPathError if a key/index is missing or if the placeholder is applied to a non-list.
    """
    keys = path.split(".")

    def helper(current, keys_remaining):
        if not keys_remaining:
            return current

        key = keys_remaining[0]
        if key == "<x>":
            # Ensure current is a list before iterating
            if not isinstance(current, list):
                raise JSONPathError(path, f"Expected list for '<x>' placeholder, got {type(current).__name__}")
            # Apply the rest of the keys to each element in the list
            results = []
            for item in current:
                results.append(helper(item, keys_remaining[1:]))
            return results
        else:
            # Handle numeric keys for list indices (e.g., '0', '1', etc.)
            if key.isdigit():
                key = int(key)
            try:
                next_value = current[key]
            except (KeyError, IndexError, TypeError) as e:
                raise JSONPathError(path, f"Invalid JSON path at {str(e)}")
            return helper(next_value, keys_remaining[1:])

    return helper(json_data, keys)

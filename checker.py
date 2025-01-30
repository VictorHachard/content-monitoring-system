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
    require_javascript_path = os.path.join(storage_dir, 'require_javascript.json')
    previous_data = load_data(previous_data_path)
    missing_data = load_data(missing_data_path)
    require_javascript_data = load_data(require_javascript_path)
    current_data = {}

    for url, rule in rules.items():
        selectors = rule.get("selectors", [])
        logging.debug(f"Checking {url} with selectors: {selectors}")
        use_selenium = rule.get("use_selenium", False)

        try:
            page_content = fetch_page_content(url, use_selenium, selenium_session)
            soup = BeautifulSoup(page_content, 'html.parser')
            for tag in soup.find_all(["script", "style", "header", "head"]):
                tag.decompose()
            logging.debug(f"Page content fetched for {url}")
            logging.debug(f"Page content: {soup.prettify()}")
            # Check if the page content is 'This site requires Javascript in order to view all its content.'
            if "This site requires Javascript in order to view all its content." in page_content:
                logging.warning(f"Page content requires Javascript for {url}")
                if url not in require_javascript_data or not require_javascript_data[url].get("alert_sent", False):
                    require_javascript_data[url] = {"url": url, "timestamp": time.time(), "alert_sent": True}
                    save_data(require_javascript_path, require_javascript_data)
                    notif.send(
                        title="Javascript Required Alert",
                        description="The page content requires Javascript",
                        url=url,
                        fields={"URL": url},
                        color='#ffc107',
                    )
                continue
            if url in require_javascript_data:
                logging.info(f"Page content no longer requires Javascript for {url}")
                del require_javascript_data[url]
                save_data(require_javascript_path, require_javascript_data)
                notif.send(
                    title="Javascript No Longer Required Notification",
                    description="The page content no longer requires Javascript",
                    url=url,
                    fields={"URL": url},
                    color='#ffc107',
                )

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
                        title="First-Time Content Detected",
                        description="Content is being tracked for the first time.",
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
                        title="Content Change Detected",
                        description="A change has been detected on the monitored content.",
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

        except Exception as e:
            logging.error(f"Error checking {url}: {e}")
            notif.send(
                title="Exception Occurred",
                description=f"An exception occurred while checking the page: `{e}`",
                url=url,
                color='#dc3545',
            )

    save_data(previous_data_path, current_data)


def fetch_page_content(url, use_selenium=False, selenium_session=None):
    if use_selenium and selenium_session:
        # Use the shared Selenium session
        return selenium_session.fetch_page(url)
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.text

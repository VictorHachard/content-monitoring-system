import os
import json
import logging
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from notifications import send_discord_notification


def save_data(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}


def check_availability(storage_dir, discord_webhook_url, rules):
    previous_data_path = os.path.join(storage_dir, 'previous_data.json')
    missing_data_path = os.path.join(storage_dir, 'missing_elements.json')
    previous_data = load_data(previous_data_path)
    missing_data = load_data(missing_data_path)
    current_data = {}

    for url, rule in rules.items():
        selectors = rule.get("selectors", [])
        use_selenium = rule.get("use_selenium", False)

        try:
            page_content = fetch_page_content(url, use_selenium)
            soup = BeautifulSoup(page_content, 'html.parser')

            for selector in selectors:
                element = soup.select_one(selector)
                key = f"{url}:{selector}"

                if element is None:
                    logging.warning(f"Element missing for {url} with selector {selector}")
                    if key not in missing_data or not missing_data[key].get("alert_sent", False):
                        missing_data[key] = {"url": url, "selector": selector, "timestamp": time.time(), "alert_sent": True}
                        save_data(missing_data_path, missing_data)
                        send_discord_notification(
                            discord_webhook_url,
                            title="Element Missing Alert",
                            description=f"The element specified by the selector `{selector}` is missing on the page.",
                            url=url,
                            fields={"URL": url, "Selector": f"`{selector}`"},
                            color='ff0000'
                        )
                    continue

                html_content = element.prettify()
                text_content = element.get_text(strip=True)

                current_data[key] = {"html": html_content, "text": text_content}

                if key in missing_data:
                    logging.info(f"Element returned for {url} with selector {selector}")
                    del missing_data[key]
                    save_data(missing_data_path, missing_data)
                    send_discord_notification(
                        discord_webhook_url,
                        title="Element Returned Notification",
                        description=f"The element specified by the selector `{selector}` has returned to the page.",
                        url=url,
                        fields={"URL": url, "Selector": f"`{selector}`"},
                        color='00ff00'
                    )

                if key not in previous_data:
                    logging.info(f"First-time change detected for {url} with selector {selector}")
                    send_discord_notification(
                        discord_webhook_url,
                        title="First-Time Content Detected",
                        description="Content is being tracked for the first time.",
                        url=url,
                        fields={
                            "URL": url,
                            "Selector": f"`{selector}`",
                            "Data": f"`{text_content}`",
                        },
                        color='00ffcc'
                    )
                elif previous_data[key]["html"] != html_content:
                    logging.info(f"Change detected for {url} with selector {selector}")
                    send_discord_notification(
                        discord_webhook_url,
                        title="Content Change Detected",
                        description="A change has been detected on the monitored content.",
                        url=url,
                        fields={
                            "URL": url,
                            "Selector": f"`{selector}`",
                            "Old Data": f"`{previous_data[key]['text']}`" if previous_data[key]['text'] else "N/A",
                            "New Data": f"`{text_content}`",
                        },
                        color='ff5733'
                    )
                else:
                    logging.info(f"No change detected for {url} with selector {selector}")

        except Exception as e:
            logging.error(f"Error checking {url}: {e}")
            send_discord_notification(
                discord_webhook_url,
                title="Exception Occurred",
                description=f"An exception occurred while checking the page: `{e}`",
                url=url,
                color='ff0000'
            )

    save_data(previous_data_path, current_data)


def fetch_page_content(url, use_selenium):
    if use_selenium:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/chromium"  # Chromium binary location

        # Use ChromiumDriver installed in the container
        service = ChromeService("/usr/bin/chromedriver")  
        driver = webdriver.Chrome(service=service, options=options)
        try:
            driver.get(url)
            time.sleep(3)  # Allow time for JavaScript to load
            content = driver.page_source
        finally:
            driver.quit()
        return content
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

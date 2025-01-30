import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SeleniumSession:
    def __init__(self):
        # Initialize the browser session
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        self.options.binary_location = "/usr/bin/chromium"  # Chromium binary location
        self.service = ChromeService("/usr/bin/chromedriver")
        self.driver = webdriver.Chrome(service=self.service, options=self.options)

    def fetch_page(self, url):
        # Fetch page content
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            logs = self.driver.get_log("browser")
            error_logs = [entry for entry in logs if entry["level"] == "SEVERE"]

            for entry in error_logs:
                logging.info(f"JS Console Error: {entry['message']}")

            return self.driver.page_source
        except Exception as e:
            logging.error(f"Error fetching page {url} using Selenium: {e}")
            raise

    def close(self):
        # Close the browser session
        if self.driver:
            self.driver.quit()

import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options


class SeleniumSession:
    def __init__(self):
        # Initialize the browser session
        self.options = Options()
        self.options.add_argument("--headless")
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.binary_location = "/usr/bin/chromium"  # Chromium binary location
        self.service = ChromeService("/usr/bin/chromedriver")
        self.driver = webdriver.Chrome(service=self.service, options=self.options)

    def fetch_page(self, url):
        # Fetch page content
        try:
            self.driver.get(url)
            time.sleep(3)  # Allow time for JavaScript to load
            return self.driver.page_source
        except Exception as e:
            logging.error(f"Error fetching page {url} using Selenium: {e}")
            raise

    def close(self):
        # Close the browser session
        if self.driver:
            self.driver.quit()
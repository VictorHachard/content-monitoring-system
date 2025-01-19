import os
import subprocess

import requests
import logging


def get_current_image_version():
    """Get the currently running Docker image version from environment variable."""
    # Try to get version from environment variable (set in Dockerfile)
    image_tag = os.getenv("IMAGE_TAG")
    if image_tag:
        logging.info(f"Current image version: {image_tag}")
        return image_tag
    else:
        logging.warning("Could not retrieve current image version")
        return None


def get_latest_git_tag():
    """Fetch the latest Git tag from the repository."""
    try:
        output = subprocess.check_output(
            ["git", "fetch", "--tags"], stderr=subprocess.DEVNULL
        )
        latest_tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        logging.info(f"Latest git tag: {latest_tag}")
        return latest_tag
    except Exception as e:
        logging.warning(f"Failed to fetch latest git tag: {e}")
        return None


def check_for_update():
    current_version = get_current_image_version()
    latest_version = get_latest_git_tag()

    if current_version and latest_version:
        if current_version != latest_version:
            logging.info(f"New version available: {latest_version}. Please update")
            return (current_version, latest_version)
        else:
            logging.info("You are using the latest version")
            return True
    else:
        logging.warning("Could not verify version information")
        return None

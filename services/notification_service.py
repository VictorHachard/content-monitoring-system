import logging
from discord_webhook import DiscordWebhook, DiscordEmbed


class NotificationService:
    def __init__(self, webhook_url, mention_users=None, footer="Content monitoring system"):
        """
        Initialize the Notif class with webhook URL and optional user mentions.
        """
        self.webhook_url = webhook_url
        self.mention_users = mention_users or []
        self.footer = footer

    def send(self, title, description, url=None, fields=None, color=None, mention_user=True):
        """
        Send a Discord notification using the webhook URL.
        """
        if mention_user:
            mention_content = " ".join([f"<@{user}>" for user in self.mention_users]) if self.mention_users else ""
        else:
            mention_content = None

        try:
            webhook = DiscordWebhook(url=self.webhook_url, content=mention_content)
            embed = DiscordEmbed(
                title=title,
                description=description,
                color=color.replace("#", "") if color else "0"
            )

            if url:
                embed.set_url(url)

            if fields:
                for field_name, field_value in fields.items():
                    embed.add_embed_field(name=field_name, value=field_value, inline=False)

            embed.set_footer(text=self.footer)
            embed.set_timestamp()
            webhook.add_embed(embed)

            response = webhook.execute()
            logging.info(f"Notification sent: {response}")
        except Exception as e:
            logging.error(f"Failed to send notification: {e}")
            logging.exception(e)


class NotificationManager:
    def __init__(self, notification_service):
        """
        :param notification_service: An instance of NotificationService (your notification sender)
        """
        self.notif_service = notification_service
        self.templates = {
            "system_start": {
                "title": "Content Monitoring System Started",
                "description": "The content monitoring system has started successfully.",
                "color": "#0dcaf0",
                "mention_user": False,
            },
            "update_available": {
                "title": "New Version Available",
                "description": "A new version of the content monitoring system is available. Please update.",
                "color": "#ffc107",
                "mention_user": False,
            },
            "daily_summary": {
                "title": "Daily Monitoring Summary",
                "description": "Summary of monitoring results for the day.",
                "color": "#0dcaf0",
                "mention_user": False,
            },
            "first_time_webpage": {
                "title": "First-Time Webpage Content Detected",
                "description": "Tracking webpage content for the first time.",
                "color": "#0dcaf0",
            },
            "element_missing": {
                "title": "Missing Element Alert",
                "description": "The element specified if missing from the page.",
                "color": "#ffc107",
                "mention_user": False,
            },
            "element_returned": {
                "title": "Element Returned Notification",
                "description": "The element specified has returned to the page.",
                "color": "#ffc107",
                "mention_user": False,
            },
            "content_change": {
                "title": "Webpage Content Change Detected",
                "description": "A change was detected on the webpage.",
                "color": "#0d6efd",
            },
            "first_time_api": {
                "title": "First-Time API Content Detected",
                "description": "Tracking API content for the first time.",
                "color": "#0dcaf0",
            },
            "api_content_change": {
                "title": "API Content Change Detected",
                "description": "A change was detected on the API.",
                "color": "#0d6efd",
            },
            "webpage_check_failed": {
                "title": "Webpage Check Failed",
                "description": "Error fetching webpage data.",
                "color": "#dc3545",
                "mention_user": False,
            },
            "api_check_failed": {
                "title": "API Check Failed",
                "description": "Error fetching API data.",
                "color": "#dc3545",
                "mention_user": False,
            },
        }

    def send(self, key, url=None, fields=None):
        """
        Sends a notification using the template identified by `key`.
        """
        template = self.templates.get(key)
        if not template:
            raise ValueError(f"Notification template not found for key '{key}'")

        self.notif_service.send(
            title=template["title"],
            description=template["description"],
            url=url,
            fields=fields or {},
            color=template.get("color", "#0dcaf0"),
            mention_user=template.get("mention_user", True),
        )

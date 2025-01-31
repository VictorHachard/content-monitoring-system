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

    def send(self, title, description, url=None, fields=None, color=None):
        """
        Send a Discord notification using the webhook URL.
        """
        mention_content = " ".join([f"<@{user}>" for user in self.mention_users]) if self.mention_users else ""

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

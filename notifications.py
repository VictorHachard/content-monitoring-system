import logging
from discord_webhook import DiscordWebhook, DiscordEmbed


def send_discord_notification(
        webhook_url: str,
        title: str,
        description: str,
        url: str = None,
        fields: dict = None,
        color: str = None,
        footer: str = "Content monitoring system",
        mention_users: list = None
):
    """
    Send a Discord notification using a webhook.
    """
    if mention_users:
        description = " ".join([f"<@{user}>" for user in mention_users]) + "\n" + description

    webhook = DiscordWebhook(url=webhook_url)
    embed = DiscordEmbed(title=title, description=description, color=color.replace("#", "") if color else 0)

    if url:
        embed.set_url(url)

    if fields:
        for field_name, field_value in fields.items():
            embed.add_embed_field(name=field_name, value=field_value, inline=False)

    embed.set_footer(text=footer)
    embed.set_timestamp()
    webhook.add_embed(embed)

    response = webhook.execute()
    logging.info(f"Notification sent: {response}")

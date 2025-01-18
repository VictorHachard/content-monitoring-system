import logging
from discord_webhook import DiscordWebhook, DiscordEmbed


def send_discord_notification(webhook_url, title, description, url=None, fields=None, color=None, footer="Content monitoring system"):
    webhook = DiscordWebhook(url=webhook_url)
    embed = DiscordEmbed(title=title, description=description, color=color)

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

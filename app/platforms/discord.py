"""Discord webhook integration.

Docs: https://discord.com/developers/docs/resources/webhook#execute-webhook
"""

from __future__ import annotations

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class DiscordPlatform(BasePlatform):
    name = "discord"
    display_name = "Discord"
    required_settings = ("discord_webhook_url",)
    docs_url = (
        "https://discord.com/developers/docs/resources/webhook#execute-webhook"
    )

    async def publish(self, message: str, cta_url: str) -> PublishResult:
        # "wait=true" makes Discord return the created message object.
        separator = "&" if "?" in self.settings.discord_webhook_url else "?"
        response = await self.request(
            "POST",
            f"{self.settings.discord_webhook_url}{separator}wait=true",
            context=f"{self.display_name} webhook execution",
            json={"content": message},
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise PlatformError(
                f"{self.display_name}: webhook did not return message data "
                "(is wait=true supported?)"
            ) from exc

        message_id = data.get("id")
        channel_id = data.get("channel_id")
        guild_id = data.get("guild_id")

        if guild_id and channel_id and message_id:
            posted_url = (
                f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
            )
        else:
            posted_url = None

        date, time = self.utc_timestamp()
        return PublishResult(
            platform=self.display_name,
            status="success",
            posted_url=posted_url,
            # Discord channels require an invite/membership to read.
            public_access=False,
            date=date,
            time=time,
        )
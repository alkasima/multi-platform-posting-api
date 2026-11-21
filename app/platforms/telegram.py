"""Telegram Bot API integration (publishes to a public channel).

Docs: https://core.telegram.org/bots/api#sendmessage
"""

from __future__ import annotations

from app.platforms.base import BasePlatform, PlatformError, PublishResult


class TelegramPlatform(BasePlatform):
    name = "telegram"
    display_name = "Telegram"
    required_settings = ("telegram_bot_token", "telegram_chat_id")
    docs_url = "https://core.telegram.org/bots/api#sendmessage"

    API_URL = "https://api.telegram.org"

    async def publish(self, message: str, cta_url: str) -> PublishResult:
        response = await self.request(
            "POST",
            f"{self.API_URL}/bot{self.settings.telegram_bot_token}/sendMessage",
            context=f"{self.display_name} message sending",
            data={
                "chat_id": self.settings.telegram_chat_id,
                "text": message,
                "disable_web_page_preview": "false",
            },
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise PlatformError(
                f"{self.display_name}: unexpected response format"
            ) from exc

        if not payload.get("ok"):
            raise PlatformError(
                f"{self.display_name}: {payload.get('description', 'message not sent')}"
            )

        result = payload.get("result") or {}
        message_id = result.get("message_id")
        chat = result.get("chat") or {}
        username = chat.get("username")

        if message_id is None:
            raise PlatformError(
                f"{self.display_name}: response did not contain a message id"
            )

        if username:
            # Public channel -> anyone can open the permalink.
            posted_url = f"https://t.me/{username}/{message_id}"
            public_access = True
        else:
            # Private chat/group -> link requires membership in the chat.
            internal_id = str(chat.get("id", "")).replace("-100", "")
            posted_url = f"https://t.me/c/{internal_id}/{message_id}"
            public_access = False

        date, time = self.utc_timestamp()
        return PublishResult(
            platform=self.display_name,
            status="success",
            posted_url=posted_url,
            public_access=public_access,
            date=date,
            time=time,
        )
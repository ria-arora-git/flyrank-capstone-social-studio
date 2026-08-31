import os
import requests
from .social_publisher import SocialPublisher

class TelegramPublisher(SocialPublisher):
    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")

    def publish(self, variant: dict) -> dict:
        if not self.token or not self.chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing from .env")
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        res = requests.post(url, json={"chat_id": self.chat_id, "text": variant["content"]}, timeout=10)
        data = res.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data.get('description', 'unknown error')}")
        message_id = data["result"]["message_id"]
        return {
            "external_id": str(message_id),
            "preview_url": f"telegram message_id={message_id} chat={self.chat_id}",
        }
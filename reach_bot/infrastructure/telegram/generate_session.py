"""
Telethon StringSession generatori — BIR MARTA ishga tushiriladi.

Ishlatish:
    docker-compose run --rm bot python -m infrastructure.telegram.generate_session

Natijada TELETHON_SESSION=<uzun string> chiqadi — uni .env ga qo'shing.
"""
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    print("=" * 60)
    print("  Telethon Session Generator")
    print("=" * 60)
    print()
    print("API credentials: https://my.telegram.org → App configuration")
    print()

    api_id_str = input("API ID: ").strip()
    if not api_id_str.isdigit():
        print("Xato: API ID raqam bo'lishi kerak.")
        return
    api_id = int(api_id_str)
    api_hash = input("API HASH: ").strip()
    phone = input("Telefon raqam (+998XXXXXXXXX): ").strip()

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(phone=phone)

    session_string = client.session.save()
    await client.disconnect()

    print()
    print("=" * 60)
    print("  Session muvaffaqiyatli yaratildi!")
    print("  Quyidagi qatorni .env fayliga qo'shing:")
    print("=" * 60)
    print()
    print(f"TELETHON_SESSION={session_string}")
    print()


if __name__ == "__main__":
    asyncio.run(main())

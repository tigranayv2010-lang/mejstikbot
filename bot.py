"""
MAJESTIK Bot — Discord бот для семьи MAJESTIK
Разработан на discord.py 2.x
"""

import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv

from config import Config
from utils import database as db

# Загрузка .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN не найден! Создайте файл .env с вашим токеном.")
    print("   Пример: DISCORD_TOKEN=your_bot_token_here")
    sys.exit(1)


# ──────────────────────────────────────────────
#  Класс бота
# ──────────────────────────────────────────────

class MajestikBot(commands.Bot):
    """Главный класс бота MAJESTIK."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # Для on_member_join / on_member_remove
        intents.message_content = True  # Для будущих текстовых команд

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="MAJESTIK Bot — бот для управления семьёй",
        )

    async def setup_hook(self):
        """Запускается один раз при старте бота. Загрузка когов и синхронизация."""
        cfg = Config()

        # Инициализация базы данных
        await db.init_db()

        # Загрузка когов
        cog_list = [
            "cogs.welcome",
            "cogs.tickets",
            "cogs.config_cog",
            "cogs.applications",
            "cogs.vacations",
            "cogs.voice",
            "cogs.afk",
            "cogs.promotions",
            "cogs.events",
        ]

        for cog in cog_list:
            try:
                await self.load_extension(cog)
                print(f"  ✅ {cog}")
            except Exception as e:
                print(f"  ❌ {cog}: {e}")

        # Синхронизация slash-команд
        guild_id = cfg.get("guild_id")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"  🔄 Команды синхронизированы для guild {guild_id}")
        else:
            await self.tree.sync()
            print("  🔄 Команды синхронизированы глобально (может занять до часа)")

    async def on_ready(self):
        """Бот подключён и готов к работе."""
        cfg = Config()
        family = cfg.get_family_name()

        print("=" * 50)
        print(f"  🤖 {self.user.name} запущен!")
        print(f"  📋 ID: {self.user.id}")
        print(f"  👑 Семья: {family}")
        print(f"  🏠 Серверов: {len(self.guilds)}")
        print(f"  👥 Пользователей: {len(self.users)}")
        print("=" * 50)

        # Установить статус
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"за {family}",
            ),
            status=discord.Status.online,
        )

        # Автоматически сохранить guild_id, если бот на одном сервере
        if len(self.guilds) == 1 and not cfg.get("guild_id"):
            cfg.set("guild_id", self.guilds[0].id)
            print(f"  💾 Guild ID сохранён: {self.guilds[0].id}")


# ──────────────────────────────────────────────
#  Запуск
# ──────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  👑 MAJESTIK Bot")
    print("  📦 Загрузка когов...")
    print("=" * 50)

    bot = MajestikBot()
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()

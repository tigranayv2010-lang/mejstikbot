import discord
import time
import os
import aiosqlite
from discord.ext import commands
from discord import app_commands, ui

from config import Config
from utils.embeds import success_embed, error_embed, base_embed

DB_PATH = "data/events.sqlite"

async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_participants (
                message_id INTEGER,
                user_id INTEGER,
                status TEXT,
                PRIMARY KEY (message_id, user_id)
            )
        """)
        await db.commit()

async def get_participants(message_id: int):
    yes, no, late = [], [], []
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, status FROM event_participants WHERE message_id = ?", (message_id,)) as cursor:
            async for row in cursor:
                if row[1] == "yes": yes.append(row[0])
                elif row[1] == "no": no.append(row[0])
                elif row[1] == "late": late.append(row[0])
    return yes, no, late

async def set_participant(message_id: int, user_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO event_participants (message_id, user_id, status) VALUES (?, ?, ?)",
            (message_id, user_id, status)
        )
        await db.commit()

def generate_participants_text(users_list):
    if not users_list:
        return "Никого"
    mentions = [f"<@{uid}>" for uid in users_list]
    text = "\n".join(mentions)
    if len(text) > 1000:
        return "Слишком много участников для отображения."
    return text

# ──────────────────────────────────────────────
#  Модальное окно - Создание мероприятия
# ──────────────────────────────────────────────

class EventModal(ui.Modal, title="Создание мероприятия"):
    title_input = ui.TextInput(label="Название мероприятия", placeholder="Сбор на ВЗМ / Тренировка", required=True, max_length=100)
    time_input = ui.TextInput(label="Дата и время", placeholder="Сегодня в 19:00", required=True, max_length=50)
    desc_input = ui.TextInput(label="Дополнительная информация", style=discord.TextStyle.paragraph, placeholder="Место сбора, требования...", required=False, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg = Config()
        channel_id = cfg.get("events.channel_id")
        
        channel = interaction.guild.get_channel(int(channel_id)) if channel_id else interaction.channel
        if not channel:
            channel = interaction.channel

        embed = base_embed(title=f"📅 Мероприятие: {self.title_input.value}")
        embed.add_field(name="🕒 Время", value=self.time_input.value, inline=False)
        if self.desc_input.value:
            embed.add_field(name="📝 Информация", value=self.desc_input.value, inline=False)
            
        embed.add_field(name="✅ Буду (0)", value="Никого", inline=True)
        embed.add_field(name="❌ Не смогу (0)", value="Никого", inline=True)
        embed.add_field(name="⏳ Опоздаю (0)", value="Никого", inline=True)
        
        embed.set_footer(text=f"Организатор: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        msg = await channel.send(content="@everyone", embed=embed, view=EventButtonsView())
        
        await interaction.followup.send(
            embed=success_embed(f"Мероприятие успешно создано в {channel.mention}!"),
            ephemeral=True
        )


# ──────────────────────────────────────────────
#  Кнопки мероприятия
# ──────────────────────────────────────────────

class EventButtonsView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def handle_click(self, interaction: discord.Interaction, status: str):
        await interaction.response.defer()
        message_id = interaction.message.id
        user_id = interaction.user.id

        await set_participant(message_id, user_id, status)
        yes, no, late = await get_participants(message_id)

        embed = interaction.message.embeds[0]
        
        # Обновляем поля
        # Индексы полей могут съехать, если нет описания, так что ищем по эмодзи
        for i, field in enumerate(embed.fields):
            if "✅" in field.name:
                embed.set_field_at(i, name=f"✅ Буду ({len(yes)})", value=generate_participants_text(yes), inline=True)
            elif "❌" in field.name:
                embed.set_field_at(i, name=f"❌ Не смогу ({len(no)})", value=generate_participants_text(no), inline=True)
            elif "⏳" in field.name:
                embed.set_field_at(i, name=f"⏳ Опоздаю ({len(late)})", value=generate_participants_text(late), inline=True)

        await interaction.message.edit(embed=embed, view=self)

    @ui.button(label="Буду", emoji="✅", style=discord.ButtonStyle.success, custom_id="evt_yes")
    async def btn_yes(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_click(interaction, "yes")

    @ui.button(label="Не смогу", emoji="❌", style=discord.ButtonStyle.danger, custom_id="evt_no")
    async def btn_no(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_click(interaction, "no")

    @ui.button(label="Опоздаю", emoji="⏳", style=discord.ButtonStyle.secondary, custom_id="evt_late")
    async def btn_late(self, interaction: discord.Interaction, button: ui.Button):
        await self.handle_click(interaction, "late")


# ──────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────

class EventsCog(commands.Cog):
    """Система сбора реакций на мероприятия."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="event", description="Создать объявление о мероприятии")
    @app_commands.checks.has_permissions(administrator=True)
    async def event_cmd(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EventModal())


async def setup(bot: commands.Bot):
    await init_db()
    await bot.add_cog(EventsCog(bot))
    bot.add_view(EventButtonsView())

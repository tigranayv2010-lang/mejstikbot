import discord
import time
from discord.ext import commands
from discord import app_commands

from utils import database as db
from utils.embeds import base_embed

def format_time(seconds: int) -> str:
    """Форматирует секунды в строку (ЧЧ:ММ)."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    parts = []
    if hours > 0: parts.append(f"{hours} ч")
    if minutes > 0 or hours == 0: parts.append(f"{minutes} мин")
    return " ".join(parts)


class VoiceCog(commands.Cog):
    """Система автоматического учета времени в голосовых каналах."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: return

        # Определяем АФК каналы
        guild_afk = member.guild.afk_channel
        before_is_afk = before.channel and before.channel == guild_afk
        after_is_afk = after.channel and after.channel == guild_afk

        # Находится ли сейчас в валидном (не АФК) канале
        joined_valid = after.channel is not None and not after_is_afk
        # Находился ли до этого в валидном (не АФК) канале
        left_valid = before.channel is not None and not before_is_afk

        user_data = await db.get_user(member.id)
        now = time.time()

        if joined_valid and not left_valid:
            # Зашел в нормальный войс (или перешел из АФК канала)
            await db.update_user(member.id, session_start=now, current_status="voice")
            print(f"[VOICE] {member.name} начал сессию в голосовом канале.")
        
        elif left_valid and not joined_valid:
            # Вышел из войса или ушел в АФК канал
            session_start = user_data.get("session_start", 0)
            if session_start > 0:
                duration = now - session_start
                new_total = user_data["total_time"] + int(duration)
                await db.update_user(member.id, total_time=new_total, session_start=0, current_status="offline")
                print(f"[VOICE] {member.name} завершил сессию. Добавлено: {int(duration)} сек. Всего: {new_total} сек.")


    @app_commands.command(name="voice-top", description="Лидерборд по времени в голосовых каналах")
    async def voice_top(self, interaction: discord.Interaction):
        # При выводе топа прибавляем текущую сессию (если человек сидит прямо сейчас)
        top_users = await db.get_top_duty(limit=10)
        
        if not top_users:
            await interaction.response.send_message(
                embed=base_embed(title="🎙️ Лидерборд: Время в войсе", description="Пока нет данных."),
            )
            return
            
        desc = ""
        now = time.time()
        
        # Обновляем активные сессии для вывода
        display_users = []
        for user in top_users:
            full_user = await db.get_user(user['user_id'])
            total = full_user['total_time']
            if full_user['session_start'] > 0:
                total += int(now - full_user['session_start'])
            display_users.append({"id": user['user_id'], "time": total})
            
        # Сортируем заново с учетом текущей сессии
        display_users.sort(key=lambda x: x["time"], reverse=True)
            
        for i, u in enumerate(display_users, 1):
            member = interaction.guild.get_member(u['id'])
            name = member.mention if member else f"<@{u['id']}>"
            
            # Эмодзи для топ-3
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            
            desc += f"{medal} {name} — **{format_time(u['time'])}**\n"
            
        embed = base_embed(title="🎙️ Лидерборд: Время в войсе", description=desc)
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="voice-info", description="Моя статистика в голосовых каналах")
    async def voice_info(self, interaction: discord.Interaction):
        user_data = await db.get_user(interaction.user.id)
        
        total = user_data["total_time"]
        if user_data["session_start"] > 0:
            total += int(time.time() - user_data["session_start"])
            status = "🟢 Сейчас в войсе"
        else:
            status = "🔴 Оффлайн / В АФК"
            
        embed = base_embed(title=f"🎙️ Статистика: {interaction.user.name}")
        embed.add_field(name="Общее время в войсе", value=f"**{format_time(total)}**", inline=False)
        embed.add_field(name="Текущий статус", value=status, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))

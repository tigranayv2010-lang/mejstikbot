import discord
import time
from discord.ext import commands
from discord import app_commands

from utils.embeds import success_embed, info_embed

class AFKCog(commands.Cog):
    """Система АФК для пользователей."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Хранение в памяти: {user_id: {"reason": "Текст", "time": timestamp}}
        self.afk_users = {}

    @app_commands.command(name="afk", description="Уйти в АФК или вернуться из него")
    @app_commands.describe(reason="Причина ухода (только при включении АФК)")
    async def afk_command(self, interaction: discord.Interaction, reason: str = "Не указана"):
        user_id = interaction.user.id
        
        if user_id in self.afk_users:
            # Возвращение из АФК
            del self.afk_users[user_id]
            
            # Попытка убрать префикс [AFK]
            try:
                if interaction.user.display_name.startswith("[AFK] "):
                    new_name = interaction.user.display_name[6:]
                    await interaction.user.edit(nick=new_name)
            except discord.Forbidden:
                pass
                
            await interaction.response.send_message(
                embed=success_embed(f"👋 С возвращением, {interaction.user.mention}! Ваш статус АФК снят.")
            )
        else:
            # Уход в АФК
            self.afk_users[user_id] = {
                "reason": reason,
                "time": time.time()
            }
            
            # Попытка добавить префикс [AFK]
            try:
                if not interaction.user.display_name.startswith("[AFK]"):
                    new_name = f"[AFK] {interaction.user.display_name}"[:32]
                    await interaction.user.edit(nick=new_name)
            except discord.Forbidden:
                pass
                
            await interaction.response.send_message(
                embed=success_embed(f"💤 {interaction.user.mention} ушел в АФК.\n\n**Причина:** {reason}")
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Проверяем, упомянули ли кого-то из АФК
        if message.mentions:
            for mention in message.mentions:
                if mention.id in self.afk_users and mention.id != message.author.id:
                    afk_data = self.afk_users[mention.id]
                    time_str = f"<t:{int(afk_data['time'])}:R>"
                    
                    embed = info_embed(
                        title="💤 Пользователь в АФК",
                        description=f"**{mention.display_name}** сейчас отошел.\n**Причина:** {afk_data['reason']}\n**Ушел:** {time_str}"
                    )
                    await message.channel.send(embed=embed, delete_after=15)
                    # Выводим только для первого найденного АФКшера, чтобы не спамить
                    break


async def setup(bot: commands.Bot):
    await bot.add_cog(AFKCog(bot))

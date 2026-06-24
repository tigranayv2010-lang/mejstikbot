import discord
from discord.ext import commands
from discord import app_commands, ui

from config import Config
from utils.embeds import success_embed, error_embed, base_embed


# ──────────────────────────────────────────────
#  Модальное окно - Заявка на отпуск
# ──────────────────────────────────────────────

class VacationModal(ui.Modal, title="Заявка на отпуск"):
    date_start = ui.TextInput(label="Дата начала", placeholder="ДД.ММ.ГГГГ", required=True, max_length=20)
    date_end = ui.TextInput(label="Дата окончания", placeholder="ДД.ММ.ГГГГ", required=True, max_length=20)
    reason = ui.TextInput(label="Причина отпуска", style=discord.TextStyle.paragraph, placeholder="Уезжаю, проблемы со светом и т.д.", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = Config()
        channel_id = cfg.get("vacations.channel_id")
        
        if not channel_id:
            await interaction.response.send_message(
                embed=error_embed("Канал для отпусков не настроен! Обратитесь к администрации."),
                ephemeral=True
            )
            return
            
        channel = interaction.guild.get_channel(int(channel_id))
        if not channel:
            await interaction.response.send_message(
                embed=error_embed("Настроенный канал для отпусков не найден!"),
                ephemeral=True
            )
            return

        embed = base_embed(title="🌴 Заявка на отпуск")
        embed.add_field(name="Сотрудник", value=interaction.user.mention, inline=False)
        embed.add_field(name="Период", value=f"С **{self.date_start.value}** по **{self.date_end.value}**", inline=False)
        embed.add_field(name="Причина", value=self.reason.value, inline=False)
        
        await channel.send(embed=embed, view=VacationReviewView())
        await interaction.response.send_message(
            embed=success_embed("Ваша заявка на отпуск успешно отправлена!"),
            ephemeral=True
        )


# ──────────────────────────────────────────────
#  Кнопки админов для рассмотрения отпуска
# ──────────────────────────────────────────────

class VacationReviewView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Одобрить", style=discord.ButtonStyle.success, custom_id="vac_approve")
    async def approve_btn(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "🌴 Заявка на отпуск [ОДОБРЕНА]"
        embed.add_field(name="Решение принял", value=f"✅ Одобрено администратором {interaction.user.mention}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)

    @ui.button(label="Отказать", style=discord.ButtonStyle.danger, custom_id="vac_deny")
    async def deny_btn(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "🌴 Заявка на отпуск [ОТКЛОНЕНА]"
        embed.add_field(name="Решение принял", value=f"❌ Отказано администратором {interaction.user.mention}", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)


# ──────────────────────────────────────────────
#  Панель для взятия отпуска
# ──────────────────────────────────────────────

class VacationLauncherView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🌴 Взять отпуск", style=discord.ButtonStyle.primary, custom_id="vac_launcher")
    async def apply_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(VacationModal())


# ──────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────

class VacationsCog(commands.Cog):
    """Система отпусков."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="vacation-panel", description="Отправить панель для взятия отпуска")
    @app_commands.checks.has_permissions(administrator=True)
    async def vac_panel(self, interaction: discord.Interaction):
        embed = base_embed(
            title="🌴 Отпуски",
            description="Если вам нужно взять перерыв, нажмите на кнопку ниже и заполните форму."
        )
        await interaction.channel.send(embed=embed, view=VacationLauncherView())
        await interaction.response.send_message(embed=success_embed("Панель отпусков отправлена!"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VacationsCog(bot))
    bot.add_view(VacationLauncherView())
    bot.add_view(VacationReviewView())

import discord
import asyncio
from discord.ext import commands
from discord import app_commands, ui

from config import Config
from utils.embeds import success_embed, error_embed, base_embed

# ──────────────────────────────────────────────
#  Вспомогательная функция для удаления канала
# ──────────────────────────────────────────────

async def delete_promo_channel(interaction: discord.Interaction, status: str):
    try:
        await interaction.channel.send(
            embed=base_embed(
                title=f"Отчет {status}", 
                description="Канал будет удален через **10 секунд**...",
                color=discord.Color.orange()
            )
        )
        await asyncio.sleep(10)
        await interaction.channel.delete(reason="Отчет на повышение рассмотрен")
    except:
        pass


# ──────────────────────────────────────────────
#  Модальное окно - Заявка на повышение
# ──────────────────────────────────────────────

class PromotionModal(ui.Modal, title="Заявка на повышение"):
    name = ui.TextInput(label="Ваш ник", placeholder="Иван | ivan123", required=True, max_length=50)
    rank = ui.TextInput(label="С какого на какой ранг?", placeholder="с 1 на 2", required=True, max_length=50)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg = Config()
        guild = interaction.guild
        member = interaction.user
        
        # Защита от спама каналами
        existing = [ch for ch in guild.text_channels if ch.name.startswith(f"повышение-{member.name.lower()}")]
        if existing:
            await interaction.followup.send(
                embed=error_embed(f"У вас уже есть открытая заявка: {existing[0].mention}"),
                ephemeral=True
            )
            return

        category_id = cfg.get("promotions.category_id")
        category_obj = None

        if category_id:
            category_obj = guild.get_channel(int(category_id))

        if category_obj is None:
            category_obj = discord.utils.get(guild.categories, name="📈 Повышения")
            if category_obj is None:
                category_obj = await guild.create_category("📈 Повышения")
                cfg.set("promotions.category_id", category_obj.id)

        # Права доступа
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                embed_links=True,
                read_message_history=True,
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
            ),
        }

        admin_role_id = cfg.get("admin_role_id")
        if admin_role_id:
            admin_role = guild.get_role(int(admin_role_id))
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True,
                    read_message_history=True,
                )

        # Создание канала
        channel_name = f"повышение-{member.name.lower()}"
        promo_channel = await guild.create_text_channel(
            name=channel_name,
            category=category_obj,
            overwrites=overwrites,
            topic=f"Заявка на повышение от {member.display_name}",
        )

        embed = base_embed(title="📈 Заявка на повышение")
        embed.add_field(name="Ник", value=self.name.value, inline=False)
        embed.add_field(name="Ранг", value=self.rank.value, inline=False)
        embed.add_field(name="Скриншоты работы", value="*Прикрепите скриншоты проделанной работы прямо в этот канал.*", inline=False)
        
        embed.add_field(name="Пользователь", value=member.mention, inline=False)
        embed.add_field(name="ID", value=str(member.id), inline=False)
        
        ping_content = member.mention
        if admin_role_id:
            ping_content += f" | <@&{admin_role_id}>"

        await promo_channel.send(content=ping_content, embed=embed, view=PromotionReviewView())
        
        await interaction.followup.send(
            embed=success_embed(f"Канал для отчета успешно создан! Перейдите в {promo_channel.mention} и скиньте доказательства работы."),
            ephemeral=True
        )


# ──────────────────────────────────────────────
#  Модальное окно - Причина отказа
# ──────────────────────────────────────────────

class PromoDenyReasonModal(ui.Modal, title="Причина отказа"):
    reason = ui.TextInput(
        label="Причина отказа", 
        style=discord.TextStyle.paragraph, 
        placeholder="Мало работы / скрины без /time...", 
        required=True
    )

    def __init__(self, applicant_id: int, original_message: discord.Message):
        super().__init__()
        self.applicant_id = applicant_id
        self.original_message = original_message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        cfg = Config()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        
        if member:
            try:
                family = cfg.get_family_name()
                embed = error_embed(f"Ваш отчет на повышение в семье **{family}** отклонен.")
                embed.add_field(name="Причина:", value=self.reason.value, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
                
        embed = self.original_message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "📈 Заявка на повышение [ОТКЛОНЕНО]"
        embed.add_field(name="Отклонил", value=interaction.user.mention, inline=False)
        embed.add_field(name="Причина", value=self.reason.value, inline=False)
        
        await self.original_message.edit(embed=embed, view=None)
        await delete_promo_channel(interaction, "ОТКЛОНЕНА")


# ──────────────────────────────────────────────
#  Кнопки админов для рассмотрения заявки
# ──────────────────────────────────────────────

class PromotionReviewView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _get_applicant_id(self, message: discord.Message) -> int:
        embed = message.embeds[0]
        for field in embed.fields:
            if field.name == "ID":
                return int(field.value)
        return None

    @ui.button(label="Одобрить", style=discord.ButtonStyle.success, custom_id="promo_approve")
    async def approve_btn(self, interaction: discord.Interaction, button: ui.Button):
        applicant_id = self._get_applicant_id(interaction.message)
        if not applicant_id:
            await interaction.response.send_message("Ошибка: ID пользователя не найден.", ephemeral=True)
            return

        await interaction.response.defer()

        cfg = Config()
        guild = interaction.guild
        member = guild.get_member(applicant_id)
        
        if member:
            try:
                family = cfg.get_family_name()
                approve_msg = cfg.get("promotions.approve_message", "Ваш отчет на повышение одобрен!")
                embed = success_embed(f"Ваш отчет на повышение в семье **{family}** одобрен!\n\n{approve_msg}")
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
                
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "📈 Заявка на повышение [ОДОБРЕНО]"
        embed.add_field(name="Одобрил", value=interaction.user.mention, inline=False)
        
        await interaction.message.edit(embed=embed, view=None)
        await delete_promo_channel(interaction, "ОДОБРЕНА")

    @ui.button(label="Отказать", style=discord.ButtonStyle.danger, custom_id="promo_deny")
    async def deny_btn(self, interaction: discord.Interaction, button: ui.Button):
        applicant_id = self._get_applicant_id(interaction.message)
        if not applicant_id:
            await interaction.response.send_message("Ошибка: ID пользователя не найден.", ephemeral=True)
            return
        await interaction.response.send_modal(PromoDenyReasonModal(applicant_id, interaction.message))


# ──────────────────────────────────────────────
#  Панель для подачи отчета
# ──────────────────────────────────────────────

class PromotionLauncherView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="📈 Подать отчет на повышение", style=discord.ButtonStyle.primary, custom_id="promo_launcher")
    async def apply_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PromotionModal())


# ──────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────

class PromotionsCog(commands.Cog):
    """Система заявок на повышение."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="promo-panel", description="Отправить панель для заявок на повышение")
    @app_commands.checks.has_permissions(administrator=True)
    async def promo_panel(self, interaction: discord.Interaction):
        embed = base_embed(
            title="📈 Заявка на повышение",
            description="Нажмите на кнопку ниже, чтобы создать канал для вашего отчета на повышение.\nВ созданном канале вы сможете прикрепить доказательства проделанной работы."
        )
        await interaction.channel.send(embed=embed, view=PromotionLauncherView())
        await interaction.response.send_message(embed=success_embed("Панель повышений отправлена!"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(PromotionsCog(bot))
    bot.add_view(PromotionLauncherView())
    bot.add_view(PromotionReviewView())

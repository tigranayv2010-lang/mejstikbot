import discord
import asyncio
from discord.ext import commands
from discord import app_commands, ui

from config import Config
from utils.embeds import success_embed, error_embed, base_embed

# ──────────────────────────────────────────────
#  Вспомогательная функция для удаления канала
# ──────────────────────────────────────────────

async def delete_app_channel(interaction: discord.Interaction, status: str):
    try:
        await interaction.channel.send(
            embed=base_embed(
                title=f"Заявка {status}", 
                description="Канал будет удален через **10 секунд**...",
                color=discord.Color.orange()
            )
        )
        await asyncio.sleep(10)
        await interaction.channel.delete(reason="Заявка рассмотрена")
    except:
        pass


# ──────────────────────────────────────────────
#  Модальное окно - Заявка в семью
# ──────────────────────────────────────────────

class ApplicationModal(ui.Modal, title="Заявка в семью"):
    name = ui.TextInput(label="Ваше имя | ник", placeholder="Иван | ivan123", required=True, max_length=50)
    playtime = ui.TextInput(label="Сколько проводите время в игре?", placeholder="4-5 часов", required=True, max_length=50)
    age = ui.TextInput(label="Ваш возраст?", placeholder="18", required=True, max_length=10)
    video = ui.TextInput(label="Откат стрельбы", placeholder="Ссылка на видео (YouTube/Imgur...)", required=True, max_length=200)
    how_knew = ui.TextInput(label="Как узнали о семье", placeholder="От друзей / на форуме", required=True, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg = Config()
        guild = interaction.guild
        member = interaction.user
        
        # Защита от спама каналами заявок
        existing = [ch for ch in guild.text_channels if ch.name.startswith(f"заявка-{member.name.lower()}")]
        if existing:
            await interaction.followup.send(
                embed=error_embed(f"У вас уже есть открытая заявка: {existing[0].mention}"),
                ephemeral=True
            )
            return

        category_id = cfg.get("applications.category_id")
        category_obj = None

        if category_id:
            category_obj = guild.get_channel(int(category_id))

        if category_obj is None:
            category_obj = discord.utils.get(guild.categories, name="📝 Заявки")
            if category_obj is None:
                category_obj = await guild.create_category("📝 Заявки")
                cfg.set("applications.category_id", category_obj.id)

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
        channel_name = f"заявка-{member.name.lower()}"
        app_channel = await guild.create_text_channel(
            name=channel_name,
            category=category_obj,
            overwrites=overwrites,
            topic=f"Заявка на вступление от {member.display_name}",
        )

        embed = base_embed(title="📋 Заявление")
        embed.add_field(name="Ваше имя | ник", value=self.name.value, inline=False)
        embed.add_field(name="Сколько проводите время в игре?", value=self.playtime.value, inline=False)
        embed.add_field(name="Ваш возраст?", value=self.age.value, inline=False)
        embed.add_field(name="Откат стрельбы", value=self.video.value, inline=False)
        embed.add_field(name="Как узнали о семье", value=self.how_knew.value, inline=False)
        
        embed.add_field(name="Пользователь", value=member.mention, inline=False)
        embed.add_field(name="Username", value=member.name, inline=False)
        embed.add_field(name="ID", value=str(member.id), inline=False)
        
        ping_content = member.mention
        if admin_role_id:
            ping_content += f" | <@&{admin_role_id}>"

        await app_channel.send(content=ping_content, embed=embed, view=ApplicationReviewView())
        
        await interaction.followup.send(
            embed=success_embed(f"Ваша заявка успешно создана! Перейдите в канал: {app_channel.mention}"),
            ephemeral=True
        )


# ──────────────────────────────────────────────
#  Модальное окно - Причина отказа
# ──────────────────────────────────────────────

class DenyReasonModal(ui.Modal, title="Причина отказа"):
    reason = ui.TextInput(
        label="Причина отказа", 
        style=discord.TextStyle.paragraph, 
        placeholder="Укажите причину, почему заявка отклонена...", 
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
                embed = error_embed(f"Ваша заявка в семью **{family}** была отклонена.")
                embed.add_field(name="Причина:", value=self.reason.value, inline=False)
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
                
        # Обновляем оригинальное сообщение
        embed = self.original_message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "📋 Заявление [ОТКЛОНЕНО]"
        embed.add_field(name="Отклонил", value=interaction.user.mention, inline=False)
        embed.add_field(name="Причина", value=self.reason.value, inline=False)
        
        await self.original_message.edit(embed=embed, view=None)
        
        # Удаляем канал
        await delete_app_channel(interaction, "ОТКЛОНЕНА")


# ──────────────────────────────────────────────
#  Кнопки админов для рассмотрения заявки
# ──────────────────────────────────────────────

class ApplicationReviewView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _get_applicant_id(self, message: discord.Message) -> int:
        embed = message.embeds[0]
        for field in embed.fields:
            if field.name == "ID":
                return int(field.value)
        return None

    @ui.button(label="Одобрить", style=discord.ButtonStyle.success, custom_id="app_approve")
    async def approve_btn(self, interaction: discord.Interaction, button: ui.Button):
        applicant_id = self._get_applicant_id(interaction.message)
        if not applicant_id:
            await interaction.response.send_message("Ошибка: ID пользователя не найден в заявке.", ephemeral=True)
            return

        await interaction.response.defer()

        cfg = Config()
        guild = interaction.guild
        member = guild.get_member(applicant_id)
        
        if member:
            try:
                family = cfg.get_family_name()
                approve_msg = cfg.get("applications.approve_message", "Ваша заявка одобрена! Ждём вас в игре.")
                embed = success_embed(f"Ваша заявка в семью **{family}** одобрена!\n\n{approve_msg}")
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
                
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "📋 Заявление [ОДОБРЕНО]"
        embed.add_field(name="Одобрил", value=interaction.user.mention, inline=False)
        
        await interaction.message.edit(embed=embed, view=None)
        
        # Удаляем канал
        await delete_app_channel(interaction, "ОДОБРЕНА")

    @ui.button(label="Отказать", style=discord.ButtonStyle.danger, custom_id="app_deny")
    async def deny_btn(self, interaction: discord.Interaction, button: ui.Button):
        applicant_id = self._get_applicant_id(interaction.message)
        if not applicant_id:
            await interaction.response.send_message("Ошибка: ID пользователя не найден в заявке.", ephemeral=True)
            return
        await interaction.response.send_modal(DenyReasonModal(applicant_id, interaction.message))


# ──────────────────────────────────────────────
#  Панель для подачи заявки
# ──────────────────────────────────────────────

class ApplicationLauncherView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="📝 Подать заявку", style=discord.ButtonStyle.primary, custom_id="app_launcher")
    async def apply_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ApplicationModal())


# ──────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────

class ApplicationsCog(commands.Cog):
    """Система заявок в семью (отдельные каналы)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="app-panel", description="Отправить панель для подачи заявок")
    @app_commands.checks.has_permissions(administrator=True)
    async def app_panel(self, interaction: discord.Interaction):
        embed = base_embed(
            title="📝 Заявка на вступление",
            description="Нажмите на кнопку ниже, чтобы заполнить анкету на вступление в нашу семью."
        )
        await interaction.channel.send(embed=embed, view=ApplicationLauncherView())
        await interaction.response.send_message(embed=success_embed("Панель заявок отправлена!"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationsCog(bot))
    bot.add_view(ApplicationLauncherView())
    bot.add_view(ApplicationReviewView())

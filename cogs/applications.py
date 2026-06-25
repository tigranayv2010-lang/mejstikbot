import discord
import asyncio
import datetime
from discord.ext import commands
from discord import app_commands, ui

from config import Config
from utils.embeds import (
    ticket_panel_embed,
    ticket_embed,
    ticket_log_embed,
    success_embed,
    error_embed,
    base_embed,
)


# ──────────────────────────────────────────────
#  Хелпер — получить список ролей для пинга (тикеты)
# ──────────────────────────────────────────────

def _get_ticket_ping_roles(cfg: Config, guild: discord.Guild) -> list[discord.Role]:
    """Возвращает список ролей поддержки/пинга для тикетов."""
    roles = []

    # Новый формат: массив ID (support_role_ids)
    ids_list = cfg.get("tickets.support_role_ids", [])
    if isinstance(ids_list, list):
        for rid in ids_list:
            role = guild.get_role(int(rid))
            if role:
                roles.append(role)

    # Обратная совместимость: старый одиночный support_role_id
    if not roles:
        single_id = cfg.get("tickets.support_role_id")
        if single_id:
            role = guild.get_role(int(single_id))
            if role:
                roles.append(role)

    return roles


# ──────────────────────────────────────────────
#  Модальное окно — создание тикета
# ──────────────────────────────────────────────

class TicketModal(ui.Modal):
    """Модальное окно для описания тикета."""

    subject = ui.TextInput(
        label="Тема",
        style=discord.TextStyle.short,
        placeholder="Кратко опишите проблему",
        required=True,
        max_length=100,
    )
    description = ui.TextInput(
        label="Описание",
        style=discord.TextStyle.paragraph,
        placeholder="Подробно опишите вашу проблему или вопрос...",
        required=True,
        max_length=1500,
    )

    def __init__(self, category: str):
        super().__init__(title=f"Тикет — {category}")
        self.category = category

    async def on_submit(self, interaction: discord.Interaction):
        cfg = Config()
        guild = interaction.guild
        member = interaction.user

        # ── Проверка лимита открытых тикетов ──
        max_tickets = cfg.get("tickets.max_open_tickets", 3)
        existing = [
            ch
            for ch in guild.text_channels
            if ch.name.startswith(f"ticket-{member.name.lower()}")
        ]
        if len(existing) >= max_tickets:
            await interaction.response.send_message(
                embed=error_embed(
                    f"У вас уже открыто **{len(existing)}** тикетов "
                    f"(максимум: {max_tickets}). Закройте существующий тикет, "
                    f"прежде чем создавать новый."
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # ── Категория (папка каналов) ──
        category_id = cfg.get("tickets.category_id")
        category_obj = None

        if category_id:
            category_obj = guild.get_channel(int(category_id))

        if category_obj is None:
            category_obj = discord.utils.get(guild.categories, name="📩 Тикеты")
            if category_obj is None:
                category_obj = await guild.create_category("📩 Тикеты")
                cfg.set("tickets.category_id", category_obj.id)

        # ── Права доступа ──
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

        # Добавить роли поддержки (все из списка)
        support_roles = _get_ticket_ping_roles(cfg, guild)
        for support_role in support_roles:
            overwrites[support_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                manage_messages=True,
                read_message_history=True,
            )

        # Добавить роль администрации
        admin_role_id = cfg.get("tickets.admin_role_id") or cfg.get("admin_role_id")
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

        # ── Создать канал тикета ──
        ticket_number = len(existing) + 1
        channel_name = f"ticket-{member.name.lower()}-{ticket_number:02d}"

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category_obj,
            overwrites=overwrites,
            topic=f"Тикет от {member.display_name} | {self.category} | {self.subject.value}",
        )

        # ── Embed в тикете ──
        embed = ticket_embed(
            user=member,
            category=self.category,
            subject=self.subject.value,
            description=self.description.value,
        )

        created_msg = cfg.get(
            "tickets.ticket_created_message",
            "Тикет создан! Опишите вашу проблему, и мы ответим вам в ближайшее время.",
        )
        embed.add_field(name="", value=f"\n{created_msg}", inline=False)

        # Пинг: автор + все роли поддержки
        ping_parts = [member.mention]
        for role in support_roles:
            ping_parts.append(role.mention)
        ping_content = " | ".join(ping_parts)

        await ticket_channel.send(
            content=ping_content,
            embed=embed,
            view=TicketControlView(),
        )

        await interaction.followup.send(
            embed=success_embed(f"Тикет создан: {ticket_channel.mention}"),
            ephemeral=True,
        )


# ──────────────────────────────────────────────
#  Select Menu — выбор категории
# ──────────────────────────────────────────────

class CategorySelect(ui.Select):
    """Выпадающий список для выбора категории тикета."""

    def __init__(self):
        cfg = Config()
        categories = cfg.get("tickets.categories", ["Поддержка", "Жалоба", "Вопрос", "Другое"])

        emoji_map = {
            "Поддержка": "🛠️",
            "Жалоба": "⚠️",
            "Вопрос": "❓",
            "Предложение": "💡",
            "Другое": "📌",
        }

        options = []
        for cat in categories:
            emoji = emoji_map.get(cat, "📋")
            options.append(
                discord.SelectOption(label=cat, emoji=emoji, value=cat)
            )

        super().__init__(
            placeholder="Выберите категорию тикета...",
            options=options,
            custom_id="ticket:category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        await interaction.response.send_modal(TicketModal(category))


class CategorySelectView(ui.View):
    """View с выбором категории. Ephemeral — не нужен persistent."""

    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(CategorySelect())


# ──────────────────────────────────────────────
#  Persistent — кнопка создания тикета (панель)
# ──────────────────────────────────────────────

class TicketLauncherView(ui.View):
    """Кнопка «Создать тикет» на панели. Persistent."""

    def __init__(self):
        super().__init__(timeout=None)
        cfg = Config()
        label = cfg.get("tickets.panel_button_label", "Создать тикет")
        emoji = cfg.get("tickets.panel_button_emoji", "📩")
        self.create_btn.label = label
        self.create_btn.emoji = emoji

    @ui.button(
        label="Создать тикет",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket:launcher_create",
    )
    async def create_btn(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            embed=base_embed(
                title="📋 Выберите категорию",
                description="Выберите категорию тикета из списка ниже:",
            ),
            view=CategorySelectView(),
            ephemeral=True,
        )


# ──────────────────────────────────────────────
#  Persistent — управление тикетом (в канале тикета)
# ──────────────────────────────────────────────

class TicketCloseConfirmView(ui.View):
    """Подтверждение закрытия тикета."""

    def __init__(self):
        super().__init__(timeout=30)

    @ui.button(label="✅ Да, закрыть", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        cfg = Config()
        channel = interaction.channel

        # Отправляем лог перед удалением
        log_channel_id = cfg.get("tickets.log_channel_id")
        if log_channel_id:
            log_channel = interaction.guild.get_channel(int(log_channel_id))
            if log_channel:
                topic = channel.topic or ""
                parts = topic.split(" | ")
                author_name = parts[0].replace("Тикет от ", "") if len(parts) > 0 else "Неизвестно"
                category = parts[1] if len(parts) > 1 else "Неизвестно"

                messages = []
                async for msg in channel.history(limit=100, oldest_first=True):
                    if not msg.author.bot:
                        messages.append(
                            f"[{msg.created_at.strftime('%d.%m.%Y %H:%M')}] "
                            f"{msg.author.display_name}: {msg.content}"
                        )

                log_embed = ticket_log_embed(
                    channel_name=channel.name,
                    user=interaction.user,
                    closed_by=interaction.user,
                    category=category,
                    created_at=channel.created_at,
                )

                if messages:
                    history_text = "\n".join(messages)
                    if len(history_text) > 4000:
                        history_text = history_text[:3997] + "..."
                    log_embed.add_field(
                        name="📜 История сообщений",
                        value=f"```\n{history_text[:1024]}\n```",
                        inline=False,
                    )

                await log_channel.send(embed=log_embed)

        await interaction.response.send_message(
            embed=base_embed(
                title="🔒 Тикет закрывается",
                description="Канал будет удалён через **5 секунд**...",
                color=discord.Color.red(),
            )
        )
        await asyncio.sleep(5)
        await channel.delete(reason=f"Тикет закрыт пользователем {interaction.user}")

    @ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Закрытие отменено.", ephemeral=True)
        self.stop()


class TicketControlView(ui.View):
    """Кнопки управления тикетом. Persistent."""

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="🔒 Закрыть тикет",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
    )
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        cfg = Config()
        confirm_text = cfg.get(
            "tickets.close_confirm_text",
            "Вы уверены, что хотите закрыть тикет?",
        )
        await interaction.response.send_message(
            embed=base_embed(
                title="⚠️ Подтверждение",
                description=confirm_text,
                color=discord.Color.orange(),
            ),
            view=TicketCloseConfirmView(),
            ephemeral=True,
        )

    @ui.button(
        label="📋 Сохранить лог",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket:save_log",
    )
    async def save_log(self, interaction: discord.Interaction, button: ui.Button):
        """Сохранить лог тикета в файл и отправить."""
        await interaction.response.defer(ephemeral=True)

        messages = []
        async for msg in interaction.channel.history(limit=200, oldest_first=True):
            timestamp = msg.created_at.strftime("%d.%m.%Y %H:%M:%S")
            content = msg.content or "[embed/attachment]"
            messages.append(f"[{timestamp}] {msg.author.display_name}: {content}")

        if not messages:
            await interaction.followup.send(
                embed=error_embed("Нет сообщений для сохранения."),
                ephemeral=True,
            )
            return

        log_text = f"=== Лог тикета: {interaction.channel.name} ===\n"
        log_text += f"Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        log_text += "=" * 50 + "\n\n"
        log_text += "\n".join(messages)

        file = discord.File(
            fp=__import__("io").BytesIO(log_text.encode("utf-8")),
            filename=f"{interaction.channel.name}-log.txt",
        )

        await interaction.followup.send(
            embed=success_embed("Лог тикета сохранён!"),
            file=file,
            ephemeral=True,
        )


# ──────────────────────────────────────────────
#  Cog: Tickets
# ──────────────────────────────────────────────

class TicketsCog(commands.Cog):
    """Система тикетов."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="ticket-panel",
        description="Отправить панель создания тикетов в текущий канал",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        """Отправить embed-панель тикетов с кнопкой «Создать тикет»."""
        embed = ticket_panel_embed()
        view = TicketLauncherView()

        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=success_embed("Панель тикетов отправлена!"),
            ephemeral=True,
        )

    @ticket_panel.error
    async def ticket_panel_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=error_embed("У вас нет прав для использования этой команды."),
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
    bot.add_view(TicketLauncherView())  # Persistent views
    bot.add_view(TicketControlView())

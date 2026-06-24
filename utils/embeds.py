import discord
import datetime
from config import Config


def get_color() -> discord.Color:
    """Получить цвет embed'ов из конфигурации."""
    cfg = Config()
    return discord.Color(cfg.get_embed_color())


def base_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = None,
    timestamp: bool = True,
) -> discord.Embed:
    """Создать базовый embed в стиле MAJESTIK."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or get_color(),
    )
    if timestamp:
        embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
    return embed


def welcome_embed(member: discord.Member) -> discord.Embed:
    """Создать embed приветствия в канале."""
    cfg = Config()
    family = cfg.get_family_name()

    title = cfg.get("welcome.title", "👋 Добро пожаловать, {user}!")
    title = title.replace("{user}", member.display_name)

    desc = cfg.get("welcome.description", "Добро пожаловать на сервер **{family_name}**!")
    desc = desc.replace("{family_name}", family).replace("{user}", member.mention)

    embed = base_embed(title=title, description=desc)
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name="👤 Пользователь",
        value=f"{member.mention}",
        inline=True,
    )
    embed.add_field(
        name="🆔 ID",
        value=f"`{member.id}`",
        inline=True,
    )

    if cfg.get("welcome.show_member_count", True):
        embed.add_field(
            name="👥 Участник №",
            value=f"`{member.guild.member_count}`",
            inline=True,
        )

    if member.created_at:
        embed.add_field(
            name="📅 Аккаунт создан",
            value=discord.utils.format_dt(member.created_at, "R"),
            inline=True,
        )

    embed.set_footer(
        text=f"{family} • ID: {member.id}",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )

    return embed


def welcome_dm_embed(member: discord.Member) -> discord.Embed:
    """Создать embed приветствия в ЛС."""
    cfg = Config()
    family = cfg.get_family_name()

    title = cfg.get("welcome.dm.title", "✨ Добро пожаловать в {family_name}! ✨")
    title = title.replace("{family_name}", family)

    desc = cfg.get(
        "welcome.dm.description",
        "● Обязательно ознакомься с **правилами** в соответствующем канале\n"
        "● После этого, ты можешь оставить **заявку на вступление** в специальном канале\n\n"
        "👑 Соблюдай порядок, проявляй активность и поднимай величие семьи вместе с нами!",
    )
    desc = desc.replace("{family_name}", family)

    # Добавляем ссылки на каналы, если указаны
    rules_ch = cfg.get("welcome.dm.rules_channel_id")
    apply_ch = cfg.get("welcome.dm.apply_channel_id")

    if rules_ch:
        desc = desc.replace(
            "**правилами**",
            f"**правилами** (<#{rules_ch}>)",
        )
    if apply_ch:
        desc = desc.replace(
            "**заявку на вступление**",
            f"**заявку на вступление** (<#{apply_ch}>)",
        )

    embed = base_embed(title=title, description=desc)
    embed.set_footer(
        text=family,
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )

    return embed


def farewell_embed(member: discord.Member) -> discord.Embed:
    """Создать embed прощания."""
    cfg = Config()
    family = cfg.get_family_name()

    title = cfg.get("farewell.title", "👤 Участник покинул сервер")

    desc = cfg.get("farewell.description", "**{user}** покинул(а) сервер.")
    desc = desc.replace("{user}", member.display_name)

    embed = base_embed(title=title, description=desc)
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(
        name="👤 Пользователь",
        value=f"{member.name}",
        inline=True,
    )
    embed.add_field(
        name="🆔 ID",
        value=f"`{member.id}`",
        inline=True,
    )

    if cfg.get("farewell.show_member_count", True):
        embed.add_field(
            name="👥 Осталось участников",
            value=f"`{member.guild.member_count}`",
            inline=True,
        )

    embed.set_footer(
        text=f"{family} • ID: {member.id}",
        icon_url=member.guild.icon.url if member.guild.icon else None,
    )

    return embed


def ticket_panel_embed() -> discord.Embed:
    """Создать embed панели тикетов."""
    cfg = Config()

    title = cfg.get("tickets.panel_title", "🎫 Система тикетов")
    desc = cfg.get(
        "tickets.panel_description",
        "Если у тебя есть вопрос, жалоба или предложение — создай тикет, нажав на кнопку ниже.\n"
        "Наша команда поддержки ответит тебе в кратчайшие сроки!",
    )

    embed = base_embed(title=title, description=desc)

    categories = cfg.get("tickets.categories", [])
    if categories:
        cats_text = "\n".join(f"• {cat}" for cat in categories)
        embed.add_field(name="📋 Категории", value=cats_text, inline=False)

    embed.set_footer(text=cfg.get_family_name())

    return embed


def ticket_embed(
    user: discord.Member,
    category: str,
    subject: str,
    description: str,
) -> discord.Embed:
    """Создать embed для нового тикета."""
    cfg = Config()

    embed = base_embed(
        title=f"🎫 Тикет — {category}",
        description=f"**Тема:** {subject}\n\n{description}",
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

    embed.add_field(name="👤 Автор", value=user.mention, inline=True)
    embed.add_field(name="📋 Категория", value=category, inline=True)

    embed.set_footer(text=cfg.get_family_name())

    return embed


def ticket_log_embed(
    channel_name: str,
    user: discord.Member | discord.User,
    closed_by: discord.Member | discord.User,
    category: str,
    created_at: datetime.datetime,
) -> discord.Embed:
    """Создать embed для лога закрытого тикета."""
    cfg = Config()

    embed = base_embed(
        title="📋 Тикет закрыт",
        description=f"Канал: `{channel_name}`",
        color=discord.Color.red(),
    )

    embed.add_field(name="👤 Автор", value=f"{user.mention}", inline=True)
    embed.add_field(name="🔒 Закрыл", value=f"{closed_by.mention}", inline=True)
    embed.add_field(name="📋 Категория", value=category, inline=True)

    if created_at:
        embed.add_field(
            name="📅 Создан",
            value=discord.utils.format_dt(created_at, "F"),
            inline=True,
        )

    embed.set_footer(text=cfg.get_family_name())

    return embed


def success_embed(text: str) -> discord.Embed:
    """Быстрый embed успеха."""
    return base_embed(title="✅ Успешно", description=text, color=discord.Color.green())


def error_embed(text: str) -> discord.Embed:
    """Быстрый embed ошибки."""
    return base_embed(title="❌ Ошибка", description=text, color=discord.Color.red())


def info_embed(title: str, text: str) -> discord.Embed:
    """Быстрый embed информации."""
    return base_embed(title=f"ℹ️ {title}", description=text)

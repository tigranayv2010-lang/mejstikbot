import discord
from discord.ext import commands
from discord import app_commands

from config import Config
from utils.embeds import welcome_embed, welcome_dm_embed, farewell_embed, info_embed


# ──────────────────────────────────────────────
#  Кнопки приветствия (persistent)
# ──────────────────────────────────────────────

class WelcomeButtonsView(discord.ui.View):
    """Кнопки под приветственным сообщением. Persistent — переживают перезапуск."""

    def __init__(self):
        super().__init__(timeout=None)
        cfg = Config()
        buttons_cfg = cfg.get("welcome.buttons", {})

        # Динамически настраиваем кнопки из конфига
        wn = buttons_cfg.get("what_next", {})
        if wn.get("enabled", True):
            self.what_next_btn.label = wn.get("label", "Что дальше?")
            self.what_next_btn.emoji = wn.get("emoji", "🔹")
        else:
            self.remove_item(self.what_next_btn)

        ap = buttons_cfg.get("apply", {})
        if ap.get("enabled", True):
            self.apply_btn.label = ap.get("label", "Подать заявку")
            self.apply_btn.emoji = ap.get("emoji", "📝")
        else:
            self.remove_item(self.apply_btn)

        cs = buttons_cfg.get("contact_staff", {})
        if cs.get("enabled", True):
            self.contact_btn.label = cs.get("label", "Связаться с руководством")
            self.contact_btn.emoji = cs.get("emoji", "📞")
        else:
            self.remove_item(self.contact_btn)

        intro = buttons_cfg.get("introduce", {})
        if intro.get("enabled", True):
            self.introduce_btn.label = intro.get("label", "Представиться в общем чате")
            self.introduce_btn.emoji = intro.get("emoji", "💬")
        else:
            self.remove_item(self.introduce_btn)

    @discord.ui.button(
        label="Что дальше?",
        style=discord.ButtonStyle.primary,
        custom_id="welcome:what_next",
    )
    async def what_next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = Config()
        response_text = cfg.get(
            "welcome.buttons.what_next.response",
            "1️⃣ Ознакомься с правилами\n2️⃣ Подай заявку на вступление\n"
            "3️⃣ Представься в общем чате\n4️⃣ Общайся и веселись!",
        )
        embed = info_embed("Что дальше?", response_text)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(
        label="Подать заявку",
        style=discord.ButtonStyle.success,
        custom_id="welcome:apply",
    )
    async def apply_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = Config()
        channel_id = cfg.get("welcome.buttons.apply.channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                await interaction.response.send_message(
                    f"📝 Подать заявку можно в канале {channel.mention}!",
                    ephemeral=True,
                )
                return
        await interaction.response.send_message(
            "📝 Канал для заявок ещё не настроен. Обратитесь к администрации.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Связаться с руководством",
        style=discord.ButtonStyle.secondary,
        custom_id="welcome:contact_staff",
    )
    async def contact_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📞 Для связи с руководством создайте тикет в канале поддержки "
            "или напишите в ЛС администратору.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Представиться",
        style=discord.ButtonStyle.secondary,
        custom_id="welcome:introduce",
    )
    async def introduce_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = Config()
        channel_id = cfg.get("welcome.buttons.introduce.channel_id")
        if channel_id:
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                await interaction.response.send_message(
                    f"💬 Представься в {channel.mention}! Расскажи немного о себе.",
                    ephemeral=True,
                )
                return
        await interaction.response.send_message(
            "💬 Канал для знакомств ещё не настроен. Обратитесь к администрации.",
            ephemeral=True,
        )


# ──────────────────────────────────────────────
#  Cog: Welcome
# ──────────────────────────────────────────────

class WelcomeCog(commands.Cog):
    """Приветствия и прощания."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Отправляет приветствие в канал и в ЛС при входе участника."""
        cfg = Config()

        if not cfg.get("welcome.enabled", True):
            return

        # ── Приветствие в канале ──
        channel_id = cfg.get("welcome.channel_id")
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = welcome_embed(member)
                view = WelcomeButtonsView()
                await channel.send(embed=embed, view=view)

        # ── Приветствие в ЛС ──
        if cfg.get("welcome.dm.enabled", True):
            try:
                embed = welcome_dm_embed(member)
                await member.send(embed=embed)
            except discord.Forbidden:
                # У пользователя закрыты ЛС
                pass
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Отправляет сообщение о выходе участника."""
        cfg = Config()

        if not cfg.get("farewell.enabled", True):
            return

        channel_id = cfg.get("farewell.channel_id")
        if not channel_id:
            # Если канал прощания не указан, используем канал приветствия
            channel_id = cfg.get("welcome.channel_id")

        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = farewell_embed(member)
                await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
    bot.add_view(WelcomeButtonsView())  # Регистрация persistent view

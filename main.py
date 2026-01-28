import discord
from discord.ext import commands
from discord.ui import View, Button
import io

TOKEN = "BOT_TOKENİNİ_BURAYA_YAZ"
LOG_CHANNEL_ID = 1466030876709359680

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# 🎟️ Ticket Açma View
# =========================
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(Button(
            label="Öneri",
            style=discord.ButtonStyle.primary,
            custom_id="ticket_oneri",
            emoji="💡"
        ))

        self.add_item(Button(
            label="Soru",
            style=discord.ButtonStyle.success,
            custom_id="ticket_soru",
            emoji="❓"
        ))

        self.add_item(Button(
            label="Ban İtiraz",
            style=discord.ButtonStyle.danger,
            custom_id="ticket_ban",
            emoji="🚫"
        ))

# =========================
# 🔒 Ticket Kapatma View
# =========================
class CloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Kapat", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        messages = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            time = msg.created_at.strftime("%d.%m.%Y %H:%M")
            author = f"{msg.author.name}#{msg.author.discriminator}"
            content = msg.content if msg.content else "[Embed / Dosya]"
            messages.append(f"[{time}] {author}: {content}")

        transcript_text = "\n".join(messages)

        file = discord.File(
            fp=io.BytesIO(transcript_text.encode("utf-8")),
            filename=f"transcript-{interaction.channel.name}.txt"
        )

        await log_channel.send(
            content=(
                f"📁 **Ticket Log**\n"
                f"👮 Kapatan Yetkili: **{interaction.user}**\n"
                f"📌 Kanal: `{interaction.channel.name}`"
            ),
            file=file
        )

        await interaction.response.send_message(
            "✅ Ticket kapatıldı ve log alındı.",
            ephemeral=True
        )

        await interaction.channel.delete()

# =========================
# 🎯 Buton Etkileşimleri
# =========================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if not interaction.type == discord.InteractionType.component:
        return

    guild = interaction.guild
    user = interaction.user

    if interaction.data["custom_id"].startswith("ticket_"):

        ticket_type = interaction.data["custom_id"].replace("ticket_", "")
        channel_name = f"ticket-{ticket_type}-{user.name}".lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        await channel.send(
            f"👋 {user.mention}\n"
            f"**İhtiyacınıza yönelik butonu kullandınız.**\n"
            f"Lütfen talebinizi detaylı şekilde yazın.",
            view=CloseView()
        )

        await interaction.response.send_message(
            f"🎟️ Ticket oluşturuldu: {channel.mention}",
            ephemeral=True
        )

# =========================
# 📌 Ticket Panel Gönderme Komutu
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    await ctx.send(
        "**🎫 Ticket Sistemi**\n"
        "İhtiyacınıza uygun butonu kullanın:",
        view=TicketView()
    )

# =========================
# ✅ Bot Hazır
# =========================
@bot.event
async def on_ready():
    print(f"Bot giriş yaptı: {bot.user}")

bot.run(TOKEN)

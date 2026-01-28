import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import asyncio
from datetime import datetime

# ================== KEEP ALIVE (RENDER + UPTIMEROBOT) ==================
app = Flask("")

@app.route("/")
def home():
    return "Bot aktif!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================== AYARLAR ==================
TOKEN = os.getenv("TOKEN")

KATEGORI_ID = 1466029294097530942
LOG_KANAL_ID = 1466030876709359680
YETKILI_ROL_IDLERI = [
    1465056480871845949,
    1465050726576427263,
    1253285883826929810
]

if not TOKEN:
    raise RuntimeError("TOKEN environment variable bulunamadı!")

# ================== BOT ==================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} aktif!")

# ================== TRANSCRIPT ==================
async def create_transcript(channel):
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        time = msg.created_at.strftime("%d.%m.%Y %H:%M")
        messages.append(f"[{time}] {msg.author}: {msg.content}")

    content = "\n".join(messages) if messages else "Mesaj yok."
    filename = f"transcript-{channel.name}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return filename

# ================== TICKET KAPATMA ==================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket Kapat", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.id in YETKILI_ROL_IDLERI for r in interaction.user.roles):
            return await interaction.response.send_message(
                "Bu işlemi sadece yetkililer yapabilir.", ephemeral=True
            )

        await interaction.response.send_message("Ticket kapatılıyor...", ephemeral=True)

        transcript_file = await create_transcript(interaction.channel)
        log_channel = interaction.guild.get_channel(LOG_KANAL_ID)

        embed = discord.Embed(
            title="Ticket Kapatıldı",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Kanal", value=interaction.channel.name, inline=False)
        embed.add_field(name="Kapatan Yetkili", value=interaction.user.mention, inline=False)

        await log_channel.send(
            embed=embed,
            file=discord.File(transcript_file)
        )

        os.remove(transcript_file)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# ================== TICKET OLUŞTURMA ==================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction, ticket_type):
        guild = interaction.guild
        category = guild.get_channel(KATEGORI_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for role_id in YETKILI_ROL_IDLERI:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"{ticket_type}-{interaction.user.name}",
            category=category,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )

        await interaction.response.send_message(
            f"Ticket oluşturuldu: {channel.mention}", ephemeral=True
        )

        await channel.send(
            f"Hoş geldin {interaction.user.mention} 👋\n"
            "Yetkililer en kısa sürede ilgilenecektir.",
            view=CloseTicketView()
        )

    @discord.ui.button(label="💡 Öneri", style=discord.ButtonStyle.green)
    async def oneri(self, interaction, button):
        await self.create_ticket(interaction, "oneri")

    @discord.ui.button(label="❓ Soru", style=discord.ButtonStyle.blurple)
    async def soru(self, interaction, button):
        await self.create_ticket(interaction, "soru")

    @discord.ui.button(label="🚫 Ban İtiraz", style=discord.ButtonStyle.red)
    async def ban(self, interaction, button):
        await self.create_ticket(interaction, "ban-itiraz")

# ================== KOMUT ==================
@bot.command()
@commands.has_permissions(administrator=True)
async def baslat(ctx):
    embed = discord.Embed(
        title="🎫 Destek Sistemi",
        description="Lütfen ihtiyacınıza yönelik butonu kullanarak talep oluşturun.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# ================== ÇALIŞTIR ==================
keep_alive()
bot.run(TOKEN)

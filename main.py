import discord
from discord.ext import commands
import os
import asyncio
from flask import Flask
from threading import Thread

# -------------------- FLASK (WEB SERVICE) --------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# -------------------- AYARLAR --------------------
TOKEN = os.getenv("DISCORD_TOKEN")

KATEGORI_ID = 1466029294097530942
ONERI_ARSIV_KANAL_ID = 1466030876709359680
YETKILI_ROL_IDLERI = [
    1465056480871845949,
    1465050726576427263,
    1253285883826929810
]

# -------------------- BOT --------------------
class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        print(f"{self.user} ONLINE!")

bot = TicketBot()

# -------------------- TICKET KAPATMA --------------------
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket Kapat", style=discord.ButtonStyle.danger)
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button):

        yetkili = any(r.id in YETKILI_ROL_IDLERI for r in interaction.user.roles)
        sahibi = interaction.user.mention == interaction.channel.topic

        if not yetkili and not sahibi:
            return await interaction.response.send_message(
                "❌ Yetkin yok.", ephemeral=True
            )

        await interaction.response.send_message("🗑 Ticket kapatılıyor...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# -------------------- ÖNERİ ARŞİV --------------------
class OneriCevapView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📌 Cevapla ve Arşivle", style=discord.ButtonStyle.secondary)
    async def arsiv(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(r.id in YETKILI_ROL_IDLERI for r in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ Sadece yetkililer.", ephemeral=True
            )

        await interaction.response.send_message("✍️ Cevabı yaz:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        msg = await bot.wait_for("message", check=check)
        cevap = msg.content

        arsiv = interaction.guild.get_channel(ONERI_ARSIV_KANAL_ID)

        embed = discord.Embed(title="📨 Öneri Cevaplandı", color=discord.Color.gold())
        embed.add_field(name="Öneriyi Yapan", value=interaction.channel.topic, inline=False)
        embed.add_field(name="Cevaplayan", value=interaction.user.mention, inline=False)
        embed.add_field(name="Cevap", value=cevap, inline=False)

        await arsiv.send(embed=embed)
        await interaction.channel.send("✅ Arşivlendi, kanal kapatılıyor...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# -------------------- TICKET VIEW --------------------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction: discord.Interaction, ttype: str):
        guild = interaction.guild
        category = guild.get_channel(KATEGORI_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        for rid in YETKILI_ROL_IDLERI:
            rol = guild.get_role(rid)
            if rol:
                overwrites[rol] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )

        ch = await guild.create_text_channel(
            name=f"{ttype}-{interaction.user.name}".lower(),
            category=category,
            overwrites=overwrites,
            topic=interaction.user.mention
        )

        await interaction.response.send_message(
            f"🎟 Ticket açıldı: {ch.mention}", ephemeral=True
        )

        if ttype == "oneri":
            await ch.send("Önerini yaz 👇", view=OneriCevapView())

        await ch.send("İşin bitince ticketı kapat 👇", view=TicketKapatView())

    @discord.ui.button(label="🚫 Ban İtiraz", style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "ban-itiraz")

    @discord.ui.button(label="💡 Öneri", style=discord.ButtonStyle.success)
    async def oneri(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "oneri")

    @discord.ui.button(label="❓ Soru", style=discord.ButtonStyle.primary)
    async def soru(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "soru")

# -------------------- KOMUT --------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def baslat(ctx):
    embed = discord.Embed(
        title="🎫 Destek Sistemi",
        description="Bir kategori seç.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# -------------------- ÇALIŞTIR --------------------
keep_alive()
bot.run(TOKEN)

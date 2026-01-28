import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread
import asyncio

# ---------- WEB SERVER ----------
app = Flask("")

@app.route("/")
def home():
    return "Bot aktif"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ---------- AYARLAR ----------
TOKEN = os.getenv("DISCORD_TOKEN")

KATEGORI_ID = 1466029294097530942
LOG_KANAL_ID = 1466030876709359680

YETKILI_ROL_IDLERI = [
    1465056480871845949,
    1465050726576427263,
    1253285883826929810
]

# ---------- BOT ----------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} aktif!")

# ---------- TICKET VIEW ----------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction, tip):
        guild = interaction.guild
        kategori = guild.get_channel(KATEGORI_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        for rid in YETKILI_ROL_IDLERI:
            rol = guild.get_role(rid)
            if rol:
                overwrites[rol] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        kanal = await guild.create_text_channel(
            name=f"{tip}-{interaction.user.name}",
            category=kategori,
            overwrites=overwrites,
            topic=interaction.user.mention
        )

        await interaction.response.send_message(
            f"Kanal açıldı: {kanal.mention}",
            ephemeral=True
        )

        await kanal.send(
            f"{interaction.user.mention} talebini buraya yazabilirsin.",
            view=CloseTicketView()
        )

    @discord.ui.button(label="Öneri", style=discord.ButtonStyle.green)
    async def oneri(self, interaction, button):
        await self.create_ticket(interaction, "oneri")

    @discord.ui.button(label="Soru", style=discord.ButtonStyle.blurple)
    async def soru(self, interaction, button):
        await self.create_ticket(interaction, "soru")

    @discord.ui.button(label="Ban İtiraz", style=discord.ButtonStyle.red)
    async def ban_itiraz(self, interaction, button):
        await self.create_ticket(interaction, "ban-itiraz")

# ---------- TICKET KAPATMA + TRANSCRIPT LOG ----------
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Kapat", style=discord.ButtonStyle.red)
    async def kapat(self, interaction, button):
        if not any(r.id in YETKILI_ROL_IDLERI for r in interaction.user.roles):
            return await interaction.response.send_message(
                "Bu işlemi sadece yetkililer yapabilir.",
                ephemeral=True
            )

        kanal = interaction.channel
        guild = interaction.guild
        log_kanal = guild.get_channel(LOG_KANAL_ID)

        # ---- MESAJ DÖKÜMÜ ----
        transcript = []
        async for msg in kanal.history(limit=200, oldest_first=True):
            if msg.author.bot:
                continue
            transcript.append(f"[{msg.author.display_name}] {msg.content}")

        transcript_text = "\n".join(transcript)
        if not transcript_text:
            transcript_text = "Mesaj bulunamadı."

        # ---- EMBED ----
        embed = discord.Embed(
            title="🎫 Ticket Kapatıldı",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Ticket Türü",
            value=kanal.name.split("-")[0],
            inline=False
        )
        embed.add_field(
            name="Ticket Sahibi",
            value=kanal.topic or "Bilinmiyor",
            inline=False
        )
        embed.add_field(
            name="Kapatan Yetkili",
            value=interaction.user.display_name,
            inline=False
        )
        embed.add_field(
            name="Kanal",
            value=kanal.name,
            inline=False
        )

        if log_kanal:
            await log_kanal.send(embed=embed)

            # ---- TRANSCRIPT PARÇALAMA ----
            for i in range(0, len(transcript_text), 1900):
                await log_kanal.send(
                    f"```{transcript_text[i:i+1900]}```"
                )

        await kanal.send("Ticket 5 saniye içinde kapatılıyor...")
        await asyncio.sleep(5)
        await kanal.delete()

# ---------- KOMUT ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def baslat(ctx):
    embed = discord.Embed(
        title="Destek Sistemi",
        description="Lütfen ihtiyacınıza yönelik butonu kullanarak talep oluşturun.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

# ---------- START ----------
keep_alive()
bot.run(TOKEN)

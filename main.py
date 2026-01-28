import discord
from discord.ext import commands
import os
import asyncio

# --- AYARLAR ---
TOKEN = os.getenv("DISCORD_TOKEN")

KATEGORI_ID = 1466029294097530942
ONERI_ARSIV_KANAL_ID = 1466030876709359680
YETKILI_ROL_IDLERI = [
    1465056480871845949,
    1465050726576427263,
    1253285883826929810
]

# --- BOT ---
class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        print(f"{self.user} aktif ve hazır!")

bot = TicketBot()

# --- TICKET KAPATMA VIEW ---
class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Ticket Kapat",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_kapat"
    )
    async def ticket_kapat(self, interaction: discord.Interaction, button: discord.ui.Button):

        yetkili_mi = any(rol.id in YETKILI_ROL_IDLERI for rol in interaction.user.roles)
        ticket_sahibi = interaction.user.mention == interaction.channel.topic

        if not yetkili_mi and not ticket_sahibi:
            return await interaction.response.send_message(
                "❌ Bu ticketı kapatma yetkin yok.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🗑 Ticket 5 saniye içinde kapatılıyor...",
            ephemeral=False
        )

        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- ÖNERİ CEVAPLAMA VIEW ---
class OneriCevapView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📌 Cevapla ve Arşivle",
        style=discord.ButtonStyle.secondary,
        custom_id="oneri_arsivle"
    )
    async def oneri_arsivle(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not any(rol.id in YETKILI_ROL_IDLERI for rol in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ Bu işlemi sadece yetkililer yapabilir.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "✍️ Cevabı yaz:",
            ephemeral=True
        )

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        msg = await bot.wait_for("message", check=check)
        cevap = msg.content

        arsiv = interaction.guild.get_channel(ONERI_ARSIV_KANAL_ID)

        embed = discord.Embed(
            title="📨 Öneri Cevaplandı",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Öneriyi Yapan",
            value=interaction.channel.topic,
            inline=False
        )
        embed.add_field(
            name="Cevaplayan",
            value=interaction.user.mention,
            inline=False
        )
        embed.add_field(
            name="Cevap",
            value=cevap,
            inline=False
        )

        await arsiv.send(embed=embed)
        await interaction.channel.send("✅ Arşivlendi, kanal kapatılıyor...")

        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- TICKET VIEW ---
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
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
                    view_channel=True,
                    send_messages=True
                )

        channel = await guild.create_text_channel(
            name=f"{ticket_type}-{interaction.user.name}".lower(),
            category=category,
            overwrites=overwrites,
            topic=interaction.user.mention
        )

        await interaction.response.send_message(
            f"🎟 Ticket açıldı: {channel.mention}",
            ephemeral=True
        )

        if ticket_type == "oneri":
            await channel.send(
                f"{interaction.user.mention} önerini yazabilirsin 👇",
                view=OneriCevapView()
            )

        await channel.send(
            "İşlemin bittiğinde ticketı kapatabilirsin 👇",
            view=TicketKapatView()
        )

    @discord.ui.button(label="🚫 Ban İtiraz", style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "ban-itiraz")

    @discord.ui.button(label="💡 Öneri", style=discord.ButtonStyle.success)
    async def oneri(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "oneri")

    @discord.ui.button(label="❓ Soru", style=discord.ButtonStyle.primary)
    async def soru(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "soru")

# --- KOMUT ---
@bot.command()
@commands.has_permissions(administrator=True)
async def baslat(ctx):
    embed = discord.Embed(
        title="🎫 Destek Sistemi",
        description="Aşağıdan bir seçenek seç.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

bot.run(TOKEN)

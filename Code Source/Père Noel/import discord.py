import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import asyncio
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# 📁 Fichier de sauvegarde du calendrier
AVENT_FILE = "avent.json"

def load_avent_data():
    if os.path.exists(AVENT_FILE):
        with open(AVENT_FILE, "r") as f:
            return json.load(f)
    else:
        return {str(day): False for day in range(1, 25)}

def save_avent_data(data):
    with open(AVENT_FILE, "w") as f:
        json.dump(data, f)

# 📅 Chargement du calendrier
avent_data = load_avent_data()

@bot.event
async def on_ready():
    print(f"🎄 Bot connecté en tant que {bot.user}")
    await tree.sync()
    check_christmas_dms.start()

# Commande /avent
@tree.command(name="avent", description="Affiche le calendrier de l'avent")
async def avent(interaction: discord.Interaction):
    today = datetime.datetime.now().day
    month = datetime.datetime.now().month
    if month == 12 and 1 <= today <= 24:
        avent_data[str(today)] = True
        save_avent_data(avent_data)

    message = "📅 **Calendrier de l'Avent** 📅\n"
    for day in range(1, 25):
        status = "✅" if avent_data[str(day)] else "⬜"
        message += f"Jour {day}: {status}\n"
    await interaction.response.send_message(message)

# Commande /concours
@tree.command(name="concours", description="Participe au concours de Noël en postant une image")
async def concours(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🎨 Merci pour ta participation au concours de Noël ! Ton image a bien été enregistrée.",
        ephemeral=True
    )
    concours_channel = discord.utils.get(interaction.guild.text_channels, name="concours-noel")
    if concours_channel:
        await concours_channel.send(f"{interaction.user.mention} a participé au concours de Noël 🎅 !")

# Tâche automatique pour envoyer des DMs à Noël
@tasks.loop(minutes=60)
async def check_christmas_dms():
    now = datetime.datetime.now()
    if now.month == 12:
        if now.day == 24 and now.hour == 16:
            await send_christmas_dm("🎅 Le Père Noël et le Staff vous souhaite un merveilleux réveillon de Noël ! Profitez bien de cette soirée magique ✨")
        elif now.day == 25 and now.hour == 9:
            await send_christmas_dm("🎄 Le Staff vous souhaite un Joyeux Noël à toi ! Que cette journée soit remplie de bonheur, de cadeaux et de chocolat chaud ☕🎁")

async def send_christmas_dm(message):
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                try:
                    await member.send(message)
                    await asyncio.sleep(1)  # Pause pour éviter le spam
                except:
                    print(f"Impossible d’envoyer un DM à {member.name}")

bot.run("TON_TOKEN_ICI")
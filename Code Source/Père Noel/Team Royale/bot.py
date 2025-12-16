import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
import json
import os

from config import TOKEN, GUILD_ID, CATEGORY_ID, STAFF_ROLE_ID
from questions import QUESTIONS

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

# ------------------ UTILS ------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ------------------ INSCRIPTION VIEW ------------------

class InscriptionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎄 S'inscrire", style=discord.ButtonStyle.green)
    async def inscrire(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        data = load_data()

        if str(member.id) in data["users"]:
            return await interaction.response.send_message(
                "❌ Tu es déjà inscrit.", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"🎄avent-{member.name}",
            category=guild.get_channel(CATEGORY_ID),
            overwrites=overwrites
        )

        data["users"][str(member.id)] = {
            "channel_id": channel.id,
            "opened_days": []
        }
        save_data(data)

        await channel.send(
            f"🎁 Bienvenue {member.mention} !\n"
            f"Le **Calendrier de l’Avent 2026** commence le **1er décembre** 🎄"
        )

        await interaction.response.send_message(
            "✅ Inscription réussie ! Salon créé.", ephemeral=True
        )

# ------------------ CASE VIEW ------------------

class CaseView(discord.ui.View):
    def __init__(self, day):
        super().__init__(timeout=None)
        self.day = day

    @discord.ui.button(label="🎁 OUVRE TA CASE", style=discord.ButtonStyle.primary)
    async def open_case(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)

        if user_id not in data["users"]:
            return await interaction.response.send_message(
                "❌ Tu n'es pas inscrit.", ephemeral=True
            )

        if self.day in data["users"][user_id]["opened_days"]:
            return await interaction.response.send_message(
                "❌ Case déjà ouverte aujourd’hui.", ephemeral=True
            )

        question = QUESTIONS.get(self.day, "Question non définie.")
        data["users"][user_id]["opened_days"].append(self.day)
        save_data(data)

        await interaction.response.send_message(
            f"🧠 **Jour {self.day}**\n{question}\n\n"
            f"✍️ Réponds directement dans ce salon."
        )

# ------------------ TÂCHE QUOTIDIENNE ------------------

@tasks.loop(hours=24)
async def calendrier_avent():
    now = datetime.now(timezone.utc)

    if now.year == 2026 and now.month == 12 and 1 <= now.day <= 24:
        data = load_data()
        guild = bot.get_guild(GUILD_ID)

        for user in data["users"].values():
            channel = guild.get_channel(user["channel_id"])
            if channel:
                await channel.send(
                    f"🎄 **Jour {now.day}**\nClique pour ouvrir ta case !",
                    view=CaseView(now.day)
                )

# ------------------ COMMANDES STAFF ------------------

@bot.tree.command(name="valide", description="Valider la réponse du membre")
@discord.app_commands.checks.has_role(STAFF_ROLE_ID)
async def valide(interaction: discord.Interaction):
    await interaction.channel.send("✅ **Réponse validée ! Bravo 🎉**")

@bot.tree.command(name="refuse", description="Refuser la réponse du membre")
@discord.app_commands.checks.has_role(STAFF_ROLE_ID)
async def refuse(interaction: discord.Interaction):
    await interaction.channel.send("❌ **Réponse refusée. Réessaie demain 🎄**")

# ------------------ READY ------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    calendrier_avent.start()
    print(f"✅ Bot connecté : {bot.user}")

# ------------------ LANCEMENT ------------------

bot.run(TOKEN)

import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os

TOKEN = "TON_TOKEN_ICI"


# ----------- FICHIER JSON ----------- #
FILE = "events.json"

def load_events():
    if not os.path.exists(FILE):
        with open(FILE, "w") as f:
            json.dump({}, f)
    with open(FILE, "r") as f:
        return json.load(f)

def save_events():
    with open(FILE, "w") as f:
        json.dump(events, f, indent=4)


# CHARGEMENT DES EVENT
events = load_events()


# -------- CONFIG DU BOT -------- #
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    await bot.tree.sync()
    print("Slash commands synchronisées.")


# -------- COMMANDES SLASH -------- #

# /creer_event
@bot.tree.command(name="creer_event", description="Créer un événement Halloween en Octobre.")
@app_commands.describe(
    nom="Nom de l'événement",
    date="Date (YYYY-MM-DD)",
    description="Description",
    categorie="Type : concours, soirée, jeux, RP"
)
async def creer_event(interaction: discord.Interaction, nom: str, date: str, description: str, categorie: str):

    categorie = categorie.lower()
    categories_valides = ["concours", "soirée", "jeux", "rp"]

    if categorie not in categories_valides:
        return await interaction.response.send_message(
            "❌ Catégorie invalide. Choisis parmi : concours / soirée / jeux / RP"
        )

    # Vérification date
    try:
        date_event = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except:
        return await interaction.response.send_message("❌ Format de date invalide.")

    if date_event.month != 10:
        return await interaction.response.send_message("🎃 Les événements doivent se dérouler en **Octobre**.")

    if nom in events:
        return await interaction.response.send_message("❌ Un événement avec ce nom existe déjà.")

    # Enregistrement
    events[nom] = {
        "date": date,
        "description": description,
        "categorie": categorie,
        "author": interaction.user.id,
        "participants": []
    }

    save_events()

    await interaction.response.send_message(
        f"🎃 **Événement créé !**\n"
        f"📌 Nom : **{nom}**\n"
        f"📅 Date : {date}\n"
        f"📂 Catégorie : {categorie}\n"
        f"📝 Description : {description}"
    )


# /liste_events
@bot.tree.command(name="liste_events", description="Voir les événements Halloween.")
async def liste_events(interaction: discord.Interaction):

    if not events:
        return await interaction.response.send_message("🎃 Aucun événement enregistré.")

    msg = "🎃 **Événements Halloween :**\n\n"
    for nom, data in events.items():
        msg += (
            f"**• {nom}** ({data['categorie']}) – {data['date']}\n"
            f"  📝 {data['description']}\n"
            f"  👥 Participants : {len(data['participants'])}\n\n"
        )

    await interaction.response.send_message(msg)


# /inscription
@bot.tree.command(name="inscription", description="S'inscrire à un événement.")
@app_commands.describe(nom="Nom de l'événement")
async def inscription(interaction: discord.Interaction, nom: str):

    if nom not in events:
        return await interaction.response.send_message("❌ Événement introuvable.")

    if interaction.user.id in events[nom]["participants"]:
        return await interaction.response.send_message("⚠️ Tu es déjà inscrit(e) !")

    events[nom]["participants"].append(interaction.user.id)
    save_events()

    await interaction.response.send_message(f"🎉 Tu es inscrit(e) à **{nom}** !")


# /desinscription
@bot.tree.command(name="desinscription", description="Se désinscrire d’un événement.")
@app_commands.describe(nom="Nom de l'événement")
async def desinscription(interaction: discord.Interaction, nom: str):

    if nom not in events:
        return await interaction.response.send_message("❌ Événement introuvable.")

    if interaction.user.id not in events[nom]["participants"]:
        return await interaction.response.send_message("⚠️ Tu n'es pas inscrit(e) à cet événement.")

    events[nom]["participants"].remove(interaction.user.id)
    save_events()

    await interaction.response.send_message(f"❌ Tu es désinscrit(e) de **{nom}**.")


# /supprimer_event
@bot.tree.command(name="supprimer_event", description="Supprimer un événement.")
@app_commands.describe(nom="Nom de l'événement")
async def supprimer_event(interaction: discord.Interaction, nom: str):

    if nom not in events:
        return await interaction.response.send_message("❌ Cet événement n'existe pas.")

    # Optionnel : seul le créateur peut supprimer
    if interaction.user.id != events[nom]["author"]:
        return await interaction.response.send_message("❌ Seul le créateur de l'événement peut le supprimer.")

    del events[nom]
    save_events()

    await interaction.response.send_message(f"🗑️ L'événement **{nom}** a été supprimé.")


# -------- LANCEMENT -------- #
bot.run(TOKEN)

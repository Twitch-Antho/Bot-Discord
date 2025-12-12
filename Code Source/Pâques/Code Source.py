import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

# ---------------------------
# CONFIG BOT
# ---------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "data_paques.json"


# ---------------------------
# SAUVEGARDE JSON
# ---------------------------

def load_data():
    """Charge les données depuis le JSON (ou crée un fichier vide)"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data():
    """Sauvegarde les données dans le JSON"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(inventaires, f, indent=4)


# Données chargées au lancement
inventaires = load_data()


def get_user_data(user_id):
    """Initialise les données si absentes"""
    if str(user_id) not in inventaires:
        inventaires[str(user_id)] = {
            "oeufs": 0,
            "chocolats": 0,
            "rares": 0,
            "score": 0
        }
        save_data()
    return inventaires[str(user_id)]


# ---------------------------
# ÉVÉNEMENT DÉMARRAGE
# ---------------------------

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    await tree.sync()
    print("Commandes slash synchronisées !")


# ---------------------------
# VUE INTERACTIVE : CHASSE
# ---------------------------

class ChasseView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=20)
        self.user = user

    @discord.ui.button(label="Chercher un œuf 🥚", style=discord.ButtonStyle.success)
    async def chercher(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user != self.user:
            return await interaction.response.send_message(
                "Ce n'est pas ta chasse ! 🐰", ephemeral=True
            )

        # Types d'œufs trouvables
        loot = [
            ("oeuf", "🥚", 1, 60),        # 60% de chance
            ("chocolat", "🍫", 2, 35),    # 35%
            ("rare", "🐣", 5, 5)          # 5%
        ]

        # Choix pondéré
        choix = random.choices(loot, weights=[l[3] for l in loot])[0]
        item, emoji, points, _ = choix

        data = get_user_data(interaction.user.id)

        # Mise à jour inventaire
        if item == "oeuf":
            data["oeufs"] += 1
        elif item == "chocolat":
            data["chocolats"] += 1
        else:
            data["rares"] += 1

        data["score"] += points
        save_data()

        embed = discord.Embed(
            title="🎉 Tu as trouvé quelque chose !",
            description=f"Tu trouves **{emoji} {item}** (+{points} points)",
            color=discord.Color.gold()
        )

        await interaction.response.edit_message(embed=embed, view=self)


# ---------------------------
# COMMANDES SLASH
# ---------------------------

@tree.command(name="chasse", description="Lance une chasse aux œufs !")
async def chasse(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🐰 Chasse aux œufs",
        description="Clique sur le bouton pour chercher des œufs !",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=ChasseView(interaction.user))


@tree.command(name="inventaire", description="Affiche ton inventaire.")
async def inventaire(interaction: discord.Interaction):

    data = get_user_data(interaction.user.id)

    embed = discord.Embed(
        title=f"🎒 Inventaire de {interaction.user.display_name}",
        color=discord.Color.blurple()
    )

    embed.add_field(name="🥚 Œufs", value=data["oeufs"])
    embed.add_field(name="🍫 Chocolats", value=data["chocolats"])
    embed.add_field(name="🐣 Œufs rares", value=data["rares"])
    embed.add_field(name="🏆 Score total", value=data["score"], inline=False)

    await interaction.response.send_message(embed=embed)


@tree.command(name="profil", description="Voir ton profil de chasseur.")
async def profil(interaction: discord.Interaction):

    data = get_user_data(interaction.user.id)

    embed = discord.Embed(
        title=f"🌟 Profil de {interaction.user.display_name}",
        color=discord.Color.orange()
    )

    embed.add_field(name="Score", value=data["score"])
    embed.add_field(name="Niveau", value=f"{data['score'] // 10}")

    await interaction.response.send_message(embed=embed)


@tree.command(name="classement", description="Voir le top des chasseurs.")
async def classement(interaction: discord.Interaction):

    if not inventaires:
        return await interaction.response.send_message("Aucun joueur enregistré 🐣")

    tri = sorted(
        inventaires.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 Classement des chasseurs d'œufs",
        color=discord.Color.gold()
    )

    for i, (user_id, data) in enumerate(tri[:10], start=1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{i}. {user.display_name}",
            value=f"{data['score']} points",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

bot.run("VOTRE_TOKEN_ICI")

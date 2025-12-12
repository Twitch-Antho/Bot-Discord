import discord
from discord import app_commands
from discord.ext import commands
import random

# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Stockage simple en mémoire
user_points = {}
user_pokemons = {}

# Liste de Pokémons fictifs
pokemons = ["Pikachu", "Bulbizarre", "Salamèche", "Carapuce", "Evoli", "Dracaufeu"]

# Missions hacker fictives
hacker_missions = [
    "Infiltrer le serveur secret de l'entreprise X.",
    "Décrypter le mot de passe d'un ancien système.",
    "Voler les données de la planète Cyberia.",
    "Installer un virus dans le réseau Omega."
]

# -----------------------------
# Quand le bot est prêt
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} est connecté !")

# -----------------------------
# Attraper un Pokémon (/capture)
# -----------------------------
@bot.tree.command(name="capture", description="Attrape un Pokémon aléatoire")
async def capture(interaction: discord.Interaction):
    poke = random.choice(pokemons)
    user_pokemons.setdefault(interaction.user.id, []).append(poke)
    user_points[interaction.user.id] = user_points.get(interaction.user.id, 0) + 10

    embed = discord.Embed(
        title="🎉 Pokémon Capturé !",
        description=f"Tu as attrapé **{poke}** !\n+10 points",
        color=0xffd700
    )
    embed.set_footer(text=f"Tu possèdes maintenant {len(user_pokemons[interaction.user.id])} Pokémon(s).")
    await interaction.response.send_message(embed=embed)

# -----------------------------
# Voir ses Pokémons (/mespokemons)
# -----------------------------
@bot.tree.command(name="mespokemons", description="Voir tous tes Pokémon capturés")
async def mespokemons(interaction: discord.Interaction):
    pokes = user_pokemons.get(interaction.user.id, [])
    if not pokes:
        await interaction.response.send_message("Tu n'as encore capturé aucun Pokémon.")
    else:
        embed = discord.Embed(
            title=f"🐾 Pokémon de {interaction.user.name}",
            description="\n".join(pokes),
            color=0x00ffff
        )
        await interaction.response.send_message(embed=embed)

# -----------------------------
# Mission Hacker (/mission)
# -----------------------------
@bot.tree.command(name="mission", description="Reçois une mission de hacker fictive")
async def mission(interaction: discord.Interaction):
    mission = random.choice(hacker_missions)
    user_points[interaction.user.id] = user_points.get(interaction.user.id, 0) + 15

    embed = discord.Embed(
        title="💻 Mission Hacker",
        description=f"{mission}\n+15 points pour l'accomplir (fictif !)",
        color=0x8e44ad
    )
    await interaction.response.send_message(embed=embed)

# -----------------------------
# Points et niveaux (/points)
# -----------------------------
@bot.tree.command(name="points", description="Voir tes points et ton niveau")
async def points(interaction: discord.Interaction):
    pts = user_points.get(interaction.user.id, 0)
    level = pts // 50 + 1
    embed = discord.Embed(
        title=f"📊 Points de {interaction.user.name}",
        description=f"Points : {pts}\nNiveau : {level}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

# -----------------------------
# Scénarios Cyber Sécurité Défensive (/cyber_securite)
# -----------------------------

cyber_scenarios = [
    {
        "titre": "Fuite de données massive",
        "contexte": "Un groupe inconnu a réussi à exfiltrer des données sensibles depuis un serveur critique.",
        "solution": "Isoler le serveur, forcer une rotation des clés API, analyser les logs et appliquer un correctif de sécurité."
    },
    {
        "titre": "Attaque par ransomware",
        "contexte": "Un ransomware chiffre progressivement les fichiers des utilisateurs internes.",
        "solution": "Déconnecter les machines infectées, restaurer depuis les sauvegardes, et analyser le vecteur d’entrée."
    },
    {
        "titre": "Tentative de brute force sur un service SSH",
        "contexte": "Une IP inconnue tente des milliers de connexions SSH chaque minute.",
        "solution": "Activer fail2ban, limiter les IP autorisées, et exiger une authentification par clés publiques."
    },
    {
        "titre": "Injection SQL détectée",
        "contexte": "Un attaquant essaie de manipuler des requêtes SQL via un formulaire vulnérable.",
        "solution": "Mettre en place des requêtes préparées, un filtrage côté serveur et un pare-feu applicatif (WAF)."
    },
    {
        "titre": "DDoS massif sur le site principal",
        "contexte": "Un trafic anormalement élevé sature le serveur et empêche tout accès au site.",
        "solution": "Déléguer au CDN, filtrer les IP, et activer le mode anti‑DDoS."
    }
]


@bot.tree.command(name="cyber_securite", description="Scénarios cybersécurité graves avec contre-mesures défensives")
async def cyber_securite(interaction: discord.Interaction):
    scenario = random.choice(cyber_scenarios)
    user_points[interaction.user.id] = user_points.get(interaction.user.id, 0) + 20
    
    embed = discord.Embed(
        title=f"🛡️ Scénario Cyber : {scenario['titre']}",
        description=f"**Contexte :**\n{scenario['contexte']}\n\n"
                    f"**Contre-mesure proposée :**\n{scenario['solution']}\n\n"
                    f"+20 points (formation cybersécurité)",
        color=0xff0000
    )
    embed.set_footer(text="Scénario fictif — objectif pédagogique uniquement.")
    
    await interaction.response.send_message(embed=embed)

# -----------------------------

bot.run("TON_TOKEN_ICI")

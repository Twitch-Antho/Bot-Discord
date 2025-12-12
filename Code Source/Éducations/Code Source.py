import discord
from discord import app_commands
from discord.ext import commands
import random

# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Système de points simple
user_points = {}

# -----------------------------
# Quand le bot est prêt
# -----------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} est connecté !")

# -----------------------------
# Quiz Math (/quiz)
# -----------------------------
math_quiz = {
    "Collège": [
        {"question": "Combien font 12 × 8 ?", "answer": "96"},
        {"question": "Résoudre : 5x = 25", "answer": "5"},
        {"question": "Quelle est la formule de l’aire d’un cercle ?", "answer": "π*r^2"},
        {"question": "Résoudre : 3x + 7 = 16", "answer": "3"},
        {"question": "Combien font 7² ?", "answer": "49"},
        {"question": "Quel est le PGCD de 12 et 18 ?", "answer": "6"}
    ],
    "Lycée": [
        {"question": "Dériver f(x) = x²", "answer": "2x"},
        {"question": "Intégrer ∫ x dx", "answer": "1/2*x^2"},
        {"question": "Résoudre x² - 5x + 6 = 0", "answer": "2 ou 3"},
        {"question": "Simplifier (x²* x³)", "answer": "x^5"},
        {"question": "Résoudre ln(e^x) = 3", "answer": "3"},
        {"question": "Quel est le cos(π/3) ?", "answer": "1/2"}
    ]
}

@bot.tree.command(name="quiz", description="Fais un quiz de maths selon ton niveau")
@app_commands.choices(level=[
    app_commands.Choice(name="Collège", value="Collège"),
    app_commands.Choice(name="Lycée", value="Lycée")
])
async def quiz(interaction: discord.Interaction, level: app_commands.Choice[str]):
    questions = math_quiz[level.value]
    q = random.choice(questions)
    
    embed = discord.Embed(
        title=f"🧮 Quiz Maths ({level.value})",
        description=f"**Question :** {q['question']}",
        color=0x1abc9c
    )
    embed.set_footer(text="Réponds dans le chat ci-dessous. Tu as 30 secondes !")
    await interaction.response.send_message(embed=embed)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=30)
        if msg.content.lower() == q["answer"].lower():
            await interaction.followup.send(f"✅ Correct ! +10 points")
            user_points[interaction.user.id] = user_points.get(interaction.user.id, 0) + 10
        else:
            await interaction.followup.send(f"❌ Faux ! La réponse était : {q['answer']}")
    except:
        await interaction.followup.send(f"⏰ Temps écoulé ! La réponse était : {q['answer']}")

# -----------------------------
# Challenge de codage (/code)
# -----------------------------
coding_challenges = [
    "Écrire une fonction qui retourne le carré d’un nombre.",
    "Créer une boucle qui affiche les nombres de 1 à 10.",
    "Écrire un programme qui demande le nom de l’utilisateur et l’affiche.",
    "Écrire une fonction qui calcule la factorielle d’un nombre.",
    "Écrire un programme qui inverse une chaîne de caractères."
]

@bot.tree.command(name="code", description="Reçois un challenge de codage interactif")
async def code(interaction: discord.Interaction):
    challenge = random.choice(coding_challenges)
    
    embed = discord.Embed(
        title="💻 Challenge de codage",
        description=f"**Challenge :** {challenge}",
        color=0x3498db
    )
    embed.add_field(name="Exemple Python :", value=f"```python\n# Ton code ici\n```", inline=False)
    embed.set_footer(text="Tu peux répondre avec ton code dans le chat !")
    await interaction.response.send_message(embed=embed)

# -----------------------------
# Cyber-style interactif (/cyber)
# -----------------------------
cyber_messages = [
    "⚡ Alerte : intrusion détectée...",
    "🖥️ Analyse des données en cours...",
    "🚀 Système cybersécurisé : protocoles actifs."
]

@bot.tree.command(name="cyber", description="Message style hacker / cyber")
async def cyber(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(cyber_messages))

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

bot.run("TON_TOKEN_ICI")

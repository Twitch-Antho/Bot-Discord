from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import discord
from discord import app_commands
from discord.ext import commands


# ---------------------------------------------------------------------------
# Configuration générale
# ---------------------------------------------------------------------------

POINTS_FILE: Final[Path] = Path("points.json")
QUIZ_TIMEOUT: Final[int] = 30
POINTS_PER_CORRECT_ANSWER: Final[int] = 10
POINTS_PER_CHALLENGE: Final[int] = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bot-educatif")


# ---------------------------------------------------------------------------
# Données du quiz
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QuizQuestion:
    """Représente une question et toutes ses réponses acceptées."""

    question: str
    answers: tuple[str, ...]
    explanation: str


MATH_QUIZ: dict[str, tuple[QuizQuestion, ...]] = {
    "college": (
        QuizQuestion("Combien font 12 × 8 ?", ("96",), "12 × 8 = 96."),
        QuizQuestion("Résoudre : 5x = 25", ("5", "x = 5"), "On divise 25 par 5 : x = 5."),
        QuizQuestion(
            "Quelle est la formule de l'aire d'un cercle ?",
            ("πr²", "pi r²", "pi*r^2", "π*r^2"),
            "L'aire d'un cercle est π × rayon².",
        ),
        QuizQuestion("Résoudre : 3x + 7 = 16", ("3", "x = 3"), "3x = 9, donc x = 3."),
        QuizQuestion("Combien font 7² ?", ("49",), "7 × 7 = 49."),
        QuizQuestion("Quel est le PGCD de 12 et 18 ?", ("6",), "Le plus grand diviseur commun est 6."),
    ),
    "lycee": (
        QuizQuestion("Dériver f(x) = x²", ("2x", "2*x"), "La dérivée de x² est 2x."),
        QuizQuestion(
            "Quelle est une primitive de f(x) = x ?",
            ("x²/2", "1/2*x²", "x^2/2", "1/2*x^2"),
            "Une primitive de x est x²/2 + C.",
        ),
        QuizQuestion(
            "Résoudre x² - 5x + 6 = 0",
            ("2 ou 3", "3 ou 2", "2, 3", "3, 2"),
            "Le polynôme se factorise en (x - 2)(x - 3).",
        ),
        QuizQuestion("Simplifier x² × x³", ("x⁵", "x^5"), "On additionne les exposants : x²⁺³ = x⁵."),
        QuizQuestion("Résoudre ln(eˣ) = 3", ("3", "x = 3"), "ln et exp sont des fonctions réciproques."),
        QuizQuestion("Quel est cos(π/3) ?", ("1/2", "0,5", "0.5"), "cos(π/3) = 1/2."),
    ),
}

LEVEL_NAMES: Final[dict[str, str]] = {"college": "Collège", "lycee": "Lycée"}

CODING_CHALLENGES: Final[tuple[tuple[str, str], ...]] = (
    ("Carré d'un nombre", "Écris une fonction qui reçoit un nombre et retourne son carré."),
    ("Boucle simple", "Affiche tous les nombres de 1 à 10 avec une boucle."),
    ("Présentation", "Demande le prénom de l'utilisateur puis affiche un message de bienvenue."),
    ("Factorielle", "Écris une fonction qui calcule la factorielle d'un nombre entier positif."),
    ("Chaîne inversée", "Écris une fonction qui retourne une chaîne de caractères à l'envers."),
)

CYBER_MESSAGES: Final[tuple[str, ...]] = (
    "⚡ Alerte : intrusion détectée... Vérification des accès en cours.",
    "🖥️ Analyse des données en cours... Aucun fichier dangereux trouvé.",
    "🚀 Système cybersécurisé : protocoles actifs.",
)


# ---------------------------------------------------------------------------
# Gestion des points
# ---------------------------------------------------------------------------


class PointsManager:
    """Stocke les points dans un fichier JSON pour les conserver après un redémarrage."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.points: dict[str, int] = {}
        self.lock = asyncio.Lock()

    def load(self) -> None:
        if not self.file_path.exists():
            return

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            self.points = {str(user_id): int(value) for user_id, value in data.items()}
        except (OSError, ValueError, TypeError) as error:
            logger.warning("Impossible de charger %s : %s", self.file_path, error)
            self.points = {}

    def save(self) -> None:
        try:
            self.file_path.write_text(
                json.dumps(self.points, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            logger.error("Impossible d'enregistrer les points : %s", error)

    async def add(self, user_id: int, amount: int) -> int:
        async with self.lock:
            key = str(user_id)
            self.points[key] = self.points.get(key, 0) + amount
            self.save()
            return self.points[key]

    def get(self, user_id: int) -> int:
        return self.points.get(str(user_id), 0)


points_manager = PointsManager(POINTS_FILE)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------


def normalize_answer(answer: str) -> str:
    """Normalise une réponse pour accepter les espaces et accents variables."""
    answer = answer.strip().lower().replace("×", "*")
    answer = "".join(
        character
        for character in unicodedata.normalize("NFD", answer)
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(answer.split())


def level_from_points(points: int) -> int:
    """Chaque tranche de 50 points fait gagner un niveau."""
    return points // 50 + 1


def progress_bar(points: int) -> str:
    progress = points % 50
    filled = progress // 5
    return "🟩" * filled + "⬜" * (10 - filled)


# ---------------------------------------------------------------------------
# Création du bot
# ---------------------------------------------------------------------------


class EducationalBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # Nécessaire uniquement pour lire la réponse envoyée au quiz.
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.synced = False

    async def setup_hook(self) -> None:
        points_manager.load()
        if not self.synced:
            synced_commands = await self.tree.sync()
            self.synced = True
            logger.info("%d commande(s) synchronisée(s).", len(synced_commands))

    async def on_ready(self) -> None:
        logger.info("%s est connecté !", self.user)


bot = EducationalBot()


# ---------------------------------------------------------------------------
# Commande /quiz
# ---------------------------------------------------------------------------


@bot.tree.command(name="quiz", description="Réponds à une question de maths et gagne des points")
@app_commands.describe(level="Choisis ton niveau scolaire")
@app_commands.choices(
    level=[
        app_commands.Choice(name="Collège", value="college"),
        app_commands.Choice(name="Lycée", value="lycee"),
    ]
)
async def quiz(interaction: discord.Interaction, level: app_commands.Choice[str]) -> None:
    """Pose une question puis attend une réponse de l'utilisateur pendant 30 secondes."""
    question = random.choice(MATH_QUIZ[level.value])
    embed = discord.Embed(
        title=f"🧮 Quiz de maths — {LEVEL_NAMES[level.value]}",
        description=f"**Question :**\n{question.question}",
        color=discord.Color.teal(),
    )
    embed.add_field(name="⏱️ Temps restant", value=f"{QUIZ_TIMEOUT} secondes", inline=False)
    embed.set_footer(text="Écris ta réponse directement dans ce salon.")
    await interaction.response.send_message(embed=embed)

    def check(message: discord.Message) -> bool:
        return message.author.id == interaction.user.id and message.channel.id == interaction.channel_id

    try:
        answer_message = await bot.wait_for("message", check=check, timeout=QUIZ_TIMEOUT)
    except asyncio.TimeoutError:
        await interaction.followup.send(f"⏰ Temps écoulé ! La réponse était **{question.answers[0]}**.")
        return

    accepted_answers = {normalize_answer(answer) for answer in question.answers}
    if normalize_answer(answer_message.content) in accepted_answers:
        total = await points_manager.add(interaction.user.id, POINTS_PER_CORRECT_ANSWER)
        await interaction.followup.send(
            f"✅ Bonne réponse, {interaction.user.mention} ! **+{POINTS_PER_CORRECT_ANSWER} points**\n"
            f"{question.explanation}\nTotal : **{total} points**"
        )
    else:
        await interaction.followup.send(
            f"❌ Ce n'est pas la bonne réponse. La réponse attendue était **{question.answers[0]}**.\n"
            f"{question.explanation}"
        )


# ---------------------------------------------------------------------------
# Commande /code
# ---------------------------------------------------------------------------


@bot.tree.command(name="code", description="Reçois un challenge de programmation Python")
async def code_challenge(interaction: discord.Interaction) -> None:
    """Affiche un exercice Python aléatoire."""
    title, description = random.choice(CODING_CHALLENGES)
    embed = discord.Embed(
        title=f"💻 Challenge Python — {title}",
        description=description,
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="📝 Exemple de départ",
        value="```python\n# Écris ta solution ici\n```",
        inline=False,
    )
    embed.add_field(
        name="🎯 Récompense",
        value=f"Propose ta solution dans le salon pour obtenir jusqu'à **{POINTS_PER_CHALLENGE} points**.",
        inline=False,
    )
    embed.set_footer(text="Conseil : commence par découper le problème en petites étapes.")
    await interaction.response.send_message(embed=embed)


# ---------------------------------------------------------------------------
# Commandes /cyber, /points et /classement
# ---------------------------------------------------------------------------


@bot.tree.command(name="cyber", description="Affiche un message au style hacker/cyber")
async def cyber(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(random.choice(CYBER_MESSAGES))


@bot.tree.command(name="points", description="Affiche tes points, ton niveau et ta progression")
async def points(interaction: discord.Interaction) -> None:
    total = points_manager.get(interaction.user.id)
    level = level_from_points(total)
    embed = discord.Embed(
        title=f"📊 Progression de {interaction.user.display_name}",
        color=discord.Color.green(),
    )
    embed.add_field(name="Points", value=f"**{total}**", inline=True)
    embed.add_field(name="Niveau", value=f"**{level}**", inline=True)
    embed.add_field(name="Progression vers le niveau suivant", value=progress_bar(total), inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="classement", description="Affiche le classement des meilleurs élèves")
async def classement(interaction: discord.Interaction) -> None:
    if not points_manager.points:
        await interaction.response.send_message("📚 Le classement est vide pour le moment.")
        return

    ranking = sorted(points_manager.points.items(), key=lambda item: item[1], reverse=True)[:10]
    lines = []
    for position, (user_id, total) in enumerate(ranking, start=1):
        member = interaction.guild.get_member(int(user_id)) if interaction.guild else None
        name = member.display_name if member else f"Utilisateur {user_id}"
        lines.append(f"**{position}.** {name} — **{total} points**")

    embed = discord.Embed(
        title="🏆 Classement éducatif",
        description="\n".join(lines),
        color=discord.Color.gold(),
    )
    await interaction.response.send_message(embed=embed)


# ---------------------------------------------------------------------------
# Démarrage sécurisé
# ---------------------------------------------------------------------------


TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "La variable d'environnement DISCORD_TOKEN est absente. "
        "Configure-la avant de lancer le bot."
    )

bot.run(TOKEN)

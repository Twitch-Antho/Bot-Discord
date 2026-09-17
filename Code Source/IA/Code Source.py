import os
import sqlite3
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI


# =========================
# Configuration
# =========================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_data.sqlite3")
QUESTIONS_PER_DAY = 5
CATEGORY_NAME = "Questions IA"

if not DISCORD_TOKEN:
    raise RuntimeError("La variable DISCORD_TOKEN est manquante.")

if not OPENAI_API_KEY:
    raise RuntimeError("La variable OPENAI_API_KEY est manquante.")


# =========================
# Intents et clients
# =========================

intents = discord.Intents.default()
intents.message_content = False
intents.members = True

bot = commands.Bot(
    command_prefix="/",
    intents=intents,
)

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# =========================
# Base de données SQLite
# =========================

def initialize_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_questions (
                user_id INTEGER PRIMARY KEY,
                day TEXT NOT NULL,
                questions_left INTEGER NOT NULL,
                channel_id INTEGER
            )
            """
        )
        connection.commit()


def today_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_user_data(user_id: int) -> dict:
    today = today_string()

    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            """
            SELECT day, questions_left, channel_id
            FROM user_questions
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            connection.execute(
                """
                INSERT INTO user_questions
                (user_id, day, questions_left, channel_id)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, today, QUESTIONS_PER_DAY, None),
            )
            connection.commit()

            return {
                "questions_left": QUESTIONS_PER_DAY,
                "channel_id": None,
            }

        saved_day, questions_left, channel_id = row

        # Réinitialisation automatique du quota chaque jour
        if saved_day != today:
            questions_left = QUESTIONS_PER_DAY

            connection.execute(
                """
                UPDATE user_questions
                SET day = ?, questions_left = ?
                WHERE user_id = ?
                """,
                (today, questions_left, user_id),
            )
            connection.commit()

        return {
            "questions_left": questions_left,
            "channel_id": channel_id,
        }


def set_channel_id(user_id: int, channel_id: int | None) -> None:
    get_user_data(user_id)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            UPDATE user_questions
            SET channel_id = ?
            WHERE user_id = ?
            """,
            (channel_id, user_id),
        )
        connection.commit()


def consume_question(user_id: int) -> int | None:
    """
    Retire une question au quota de l'utilisateur.
    Retourne le nombre de questions restantes.
    Retourne None si le quota est épuisé.
    """
    user_data = get_user_data(user_id)

    if user_data["questions_left"] <= 0:
        return None

    questions_left = user_data["questions_left"] - 1

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            UPDATE user_questions
            SET questions_left = ?
            WHERE user_id = ?
            """,
            (questions_left, user_id),
        )
        connection.commit()

    return questions_left


def refund_question(user_id: int) -> None:
    """
    Rend une question en cas d'erreur lors de l'appel à l'IA.
    """
    user_data = get_user_data(user_id)

    questions_left = min(
        user_data["questions_left"] + 1,
        QUESTIONS_PER_DAY,
    )

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            """
            UPDATE user_questions
            SET questions_left = ?
            WHERE user_id = ?
            """,
            (questions_left, user_id),
        )
        connection.commit()


# =========================
# Fonctions utilitaires
# =========================

def is_moderator(member: discord.Member) -> bool:
    return (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_messages
    )


async def get_questions_category(
    guild: discord.Guild,
) -> discord.CategoryChannel:
    category = discord.utils.get(
        guild.categories,
        name=CATEGORY_NAME,
    )

    if category:
        return category

    return await guild.create_category(CATEGORY_NAME)


async def ask_ai(question: str) -> str:
    response = await openai_client.responses.create(
        model=OPENAI_MODEL,
        instructions=(
            "Tu es l'assistant IA d'un serveur Discord. "
            "Réponds en français, de manière claire, utile et concise. "
            "Ne prétends pas avoir accès à des informations privées. "
            "Si tu ne connais pas la réponse, indique-le honnêtement."
        ),
        input=question,
    )

    answer = response.output_text.strip()

    if not answer:
        return "Je n'ai pas réussi à générer une réponse."

    return answer


# =========================
# Événements du bot
# =========================

@bot.event
async def on_ready() -> None:
    print(f"Connecté en tant que {bot.user}.")


async def sync_commands() -> None:
    """
    Synchronise les commandes slash avec Discord.
    """
    await bot.tree.sync()
    print("Commandes slash synchronisées.")


@bot.event
async def setup_hook() -> None:
    initialize_database()
    await sync_commands()


# =========================
# Commandes slash
# =========================

@bot.tree.command(
    name="help",
    description="Affiche la liste des commandes disponibles.",
)
async def help_command(interaction: discord.Interaction) -> None:
    message = (
        "**Commandes disponibles :**\n"
        "`/questions` - Crée un salon privé pour parler à l'IA.\n"
        "`/poser question:` - Pose une question à l'IA.\n"
        "`/fermer` - Ferme ton salon privé.\n"
        "`/ia_plus` - Affiche les informations sur l'offre IA Plus."
    )

    await interaction.response.send_message(
        message,
        ephemeral=True,
    )


@bot.tree.command(
    name="questions",
    description="Crée un salon privé pour poser des questions à l'IA.",
)
async def questions_command(
    interaction: discord.Interaction,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "Cette commande doit être utilisée sur un serveur Discord.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    user_id = interaction.user.id
    user_data = get_user_data(user_id)

    # Vérifie si l'utilisateur possède déjà un salon
    if user_data["channel_id"]:
        existing_channel = interaction.guild.get_channel(
            user_data["channel_id"]
        )

        if existing_channel:
            await interaction.followup.send(
                f"Tu as déjà un salon ouvert : {existing_channel.mention}",
                ephemeral=True,
            )
            return

        # Le salon a probablement été supprimé manuellement
        set_channel_id(user_id, None)

    category = await get_questions_category(interaction.guild)

    bot_member = interaction.guild.me

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(
            view_channel=False,
        ),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
    }

    if bot_member:
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        )

    # Les modérateurs peuvent voir le salon
    for member in interaction.guild.members:
        if isinstance(member, discord.Member) and is_moderator(member):
            overwrites[member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

    channel_name = f"questions-{interaction.user.name}".lower()
    channel_name = channel_name[:90]

    channel = await interaction.guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        reason="Création d'un salon privé IA",
    )

    set_channel_id(user_id, channel.id)

    await channel.send(
        f"Bienvenue {interaction.user.mention} !\n\n"
        f"Il te reste **{user_data['questions_left']} question(s)** "
        "pour aujourd'hui.\n"
        "Utilise la commande `/poser` pour interroger l'IA."
    )

    await interaction.followup.send(
        f"Ton salon privé a été créé : {channel.mention}",
        ephemeral=True,
    )


@bot.tree.command(
    name="poser",
    description="Pose une question à l'intelligence artificielle.",
)
@app_commands.describe(question="La question à envoyer à l'IA")
async def poser_command(
    interaction: discord.Interaction,
    question: str,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "Cette commande doit être utilisée sur un serveur Discord.",
            ephemeral=True,
        )
        return

    user_id = interaction.user.id
    user_data = get_user_data(user_id)

    # Vérifie que la commande est utilisée dans le bon salon
    if user_data["channel_id"] != interaction.channel_id:
        await interaction.response.send_message(
            "Tu dois utiliser `/poser` dans ton salon privé créé avec `/questions`.",
            ephemeral=True,
        )
        return

    if not question.strip():
        await interaction.response.send_message(
            "La question ne peut pas être vide.",
            ephemeral=True,
        )
        return

    questions_left = consume_question(user_id)

    if questions_left is None:
        await interaction.response.send_message(
            "Tu as épuisé tes questions gratuites pour aujourd'hui. "
            "Utilise `/ia_plus` pour obtenir plus d'informations.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    try:
        answer = await ask_ai(question)

    except Exception as error:
        print(f"Erreur OpenAI : {error}")

        # La question est rendue si l'API rencontre une erreur
        refund_question(user_id)

        await interaction.followup.send(
            "Une erreur est survenue lors de la réponse de l'IA. "
            "Ta question a été recréditée.",
        )
        return

    if questions_left == 1:
        warning = (
            "\n\n⚠️ Il te reste **1 question** pour aujourd'hui. "
            "Utilise `/ia_plus` pour obtenir plus de questions."
        )
    elif questions_left == 0:
        warning = (
            "\n\n⚠️ Tu as utilisé toutes tes questions gratuites "
            "pour aujourd'hui."
        )
    else:
        warning = (
            f"\n\nIl te reste **{questions_left} question(s)** "
            "pour aujourd'hui."
        )

    # Discord limite la taille d'un message à 2 000 caractères
    full_response = answer + warning

    if len(full_response) <= 2000:
        await interaction.followup.send(full_response)
        return

    # Découpage pour les réponses longues
    for start in range(0, len(full_response), 2000):
        await interaction.followup.send(
            full_response[start:start + 2000]
        )


@bot.tree.command(
    name="fermer",
    description="Ferme ton salon privé de questions.",
)
async def fermer_command(
    interaction: discord.Interaction,
) -> None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "Cette commande doit être utilisée sur un serveur Discord.",
            ephemeral=True,
        )
        return

    channel = interaction.channel

    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "Cette commande doit être utilisée dans un salon texte.",
            ephemeral=True,
        )
        return

    user_id = interaction.user.id
    user_data = get_user_data(user_id)

    is_owner = user_data["channel_id"] == channel.id
    moderator = isinstance(interaction.user, discord.Member) and is_moderator(
        interaction.user
    )

    if not is_owner and not moderator:
        await interaction.response.send_message(
            "Seul le propriétaire du salon ou un modérateur peut le fermer.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        "Le salon sera supprimé dans quelques secondes.",
        ephemeral=True,
    )

    # On supprime la référence avant de supprimer le salon
    if is_owner:
        set_channel_id(user_id, None)

    await channel.delete(reason="Fermeture d'un salon privé IA")


@bot.tree.command(
    name="ia_plus",
    description="Affiche les informations sur l'offre IA Plus.",
)
async def ia_plus_command(
    interaction: discord.Interaction,
) -> None:
    message = (
        "**IA Plus**\n\n"
        "Le bot propose actuellement 5 questions gratuites par jour.\n"
        "Une offre IA Plus peut être ajoutée pour obtenir davantage de "
        "questions.\n\n"
        "Pour souscrire, ouvre un ticket auprès du support."
    )

    await interaction.response.send_message(
        message,
        ephemeral=True,
    )

bot.run(DISCORD_TOKEN)

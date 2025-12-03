import discord
from discord.ext import commands
from discord import app_commands
import time

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CONFESSION_CHANNEL_ID = 123456789012345678  # ID du salon confessions

# Pour savoir qui doit envoyer une confession en MP
waiting_for_confession = {}

# Pour gérer le cooldown (1 par jour)
cooldowns = {}  # {user_id: timestamp}


@bot.event
async def on_ready():
    print(f"Bot connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(e)

# ============================
# Slash Command: /confession
# ============================

@bot.tree.command(name="confession", description="Envoyer une confession anonyme (1 fois par jour)")
async def confession(interaction: discord.Interaction):
    user = interaction.user

    # Vérification cooldown 24h
    now = time.time()
    if user.id in cooldowns and now - cooldowns[user.id] < 86400:  # 24h = 86400s
        remaining = int((86400 - (now - cooldowns[user.id])) / 3600)
        return await interaction.response.send_message(
            f"⏳ Tu dois attendre encore **{remaining}h** avant de refaire une confession.",
            ephemeral=True
        )

    # Envoi en DM
    try:
        embed_dm = discord.Embed(
            title="📨 Confession Anonyme",
            description=(
                "Tu peux maintenant m'envoyer ta confession ici.\n"
                "**Je la publierai anonymement sur le serveur.**"
            ),
            color=0x2F3136
        )
        embed_dm.set_footer(text="Tu peux écrire un seul message.")

        await user.send(embed=embed_dm)

    except discord.Forbidden:
        return await interaction.response.send_message(
            "❌ Je ne peux pas t’envoyer de message privé ! Active tes MP.",
            ephemeral=True
        )

    # On note qu'on attend une confession de cet utilisateur
    waiting_for_confession[user.id] = True

    # Message de confirmation visible seulement par lui
    embed_confirm = discord.Embed(
        title="📩 MP envoyé !",
        description="Va dans tes messages privés pour écrire ta confession.",
        color=0x5865F2
    )
    await interaction.response.send_message(embed=embed_confirm, ephemeral=True)


# ============================
# Gestion des MP
# ============================

@bot.event
async def on_message(message):
    # Ignorer bot
    if message.author == bot.user:
        return

    # Si message vient d'un DM et que l’utilisateur doit envoyer une confession
    if isinstance(message.channel, discord.DMChannel):
        if waiting_for_confession.get(message.author.id):

            channel = bot.get_channel(CONFESSION_CHANNEL_ID)

            # Embed stylé pour la confession
            embed_confession = discord.Embed(
                title="🕶️ Nouvelle Confession Anonyme",
                description=message.content,
                color=0xFF6B6B
            )
            embed_confession.set_footer(text="Envoyé anonymement")

            await channel.send(embed=embed_confession)

            # Confirmation dans les MP
            embed_done = discord.Embed(
                title="✔️ Confession Envoyée",
                description="Ta confession a été envoyée anonymement sur le serveur.",
                color=0x57F287
            )
            await message.author.send(embed=embed_done)

            # Ajout du cooldown 24h
            cooldowns[message.author.id] = time.time()

            # Fin de l'attente
            del waiting_for_confession[message.author.id]

    await bot.process_commands(message)


bot.run("TON_TOKEN_ICI")

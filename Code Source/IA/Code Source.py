import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

# Création du bot
bot = commands.Bot(command_prefix='/', intents=intents)

# Dictionnaire pour garder la trace des questions posées
questions_data = {}

# Commande /help
@bot.command()
async def help(ctx):
    help_message = """
    Voici les commandes disponibles :
    /help - Affiche ce message d'aide
    /questions - Crée un salon privé pour poser des questions à l'IA
    /fermé - Ferme le salon de questions (seulement l'utilisateur ou les modérateurs peuvent fermer)
    /IA Plus - Informations sur le plan payant pour plus de questions
    """
    await ctx.send(help_message)

# Commande /questions pour créer un salon privé
@bot.command()
async def questions(ctx):
    user_id = ctx.author.id
    if user_id not in questions_data:
        questions_data[user_id] = {
            'questions_left': 5,
            'channel': None
        }
    
    # Créer un salon privé
    guild = ctx.guild
    category = discord.utils.get(guild.categories, name="Questions IA")  # Assure-toi d'avoir une catégorie appelée "Questions IA"
    if not category:
        category = await guild.create_category("Questions IA")

    channel = await guild.create_text_channel(f"questions-{ctx.author.name}", category=category)

    # Limiter la visibilité à l'utilisateur, les modérateurs et les admins
    overwrite = discord.PermissionOverwrite()
    overwrite.read_messages = True
    await channel.set_permissions(ctx.author, overwrite=overwrite)

    for member in guild.members:
        if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
            await channel.set_permissions(member, read_messages=True)
    
    # Stocke le salon pour l'utilisateur
    questions_data[user_id]['channel'] = channel

    await ctx.send(f"Un salon privé a été créé pour vous : {channel.mention}")
    await channel.send(f"Bienvenue {ctx.author.mention}! Vous avez 5 questions à poser à l'IA. À chaque question, vous en perdrez une. Vous avez {questions_data[user_id]['questions_left']} questions restantes.")

# Commande pour poser une question et gérer le nombre de questions
@bot.command()
async def poser(ctx, *, question: str):
    user_id = ctx.author.id
    if user_id not in questions_data or not questions_data[user_id]['channel'] == ctx.channel:
        await ctx.send("Vous devez utiliser la commande /questions pour créer un salon privé avant de poser des questions.")
        return

    if questions_data[user_id]['questions_left'] <= 0:
        await ctx.send("Vous avez épuisé vos 5 questions. Si vous souhaitez plus de questions, faites /IA Plus.")
        return
    
    questions_data[user_id]['questions_left'] -= 1
    if questions_data[user_id]['questions_left'] == 1:
        await ctx.send(f"Attention, il vous reste 1 question. Si vous voulez plus de questions, faites /IA Plus.")
    
    # Répondre à la question (ici on simule une IA avec un message par défaut)
    response = "Voici une réponse à votre question : [Réponse générée par l'IA]."
    
    await ctx.send(response)

# Commande /fermé pour supprimer le salon de questions
@bot.command()
async def fermé(ctx):
    user_id = ctx.author.id
    if user_id in questions_data and questions_data[user_id]['channel'] == ctx.channel:
        # Suppression du salon
        await ctx.channel.delete()
        questions_data[user_id]['channel'] = None
        await ctx.send(f"Le salon {ctx.channel.name} a été supprimé.")
    elif not ctx.channel.name.startswith("questions-"):
        await ctx.send("Ce salon ne fait pas partie d'une session de questions.")
    else:
        await ctx.send("Seul l'utilisateur qui a créé ce salon peut le fermer.")

# Commande /IA Plus pour expliquer le plan payant
@bot.command()
async def IA(ctx):
    IA_message = """
    Le bot IA peut répondre à 5 questions gratuites par jour. Si vous souhaitez poser plus de questions, vous pouvez souscrire à notre plan IA Plus, au prix de 3€ par mois.
    Pour plus d'informations, veuillez ouvrir un ticket de support pour effectuer l'abonnement.
    """
    await ctx.send(IA_message)

# Démarre le bot
bot.run('VOTRE_TOKEN')

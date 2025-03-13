import discord
from discord.ext import commands, tasks
import logging

# Configuration du bot
intents = discord.Intents.default()
intents.members = True  # Intention pour accéder aux événements liés aux membres
bot = commands.Bot(command_prefix='/', intents=intents)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Quand le bot est prêt
@bot.event
async def on_ready():
    print(f'Nous avons connecté {bot.user}')
    logging.info(f'{bot.user} est maintenant en ligne.')

# Quand un membre rejoint le serveur
@bot.event
async def on_member_join(member):
    # Enregistrement de l'adhésion d'un nouveau membre
    logging.info(f'Un nouveau membre a rejoint: {member.name}')
    # Auto-assignation des rôles
    role = discord.utils.get(member.guild.roles, name="Membre")
    if role:
        await member.add_roles(role)
        logging.info(f'Rôle "Membre" assigné à {member.name}')

# Suivi des messages envoyés
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignorer les messages du bot

    logging.info(f'{message.author} a envoyé un message : {message.content}')
    await bot.process_commands(message)

# Commande "/ping" pour tester la connexion
@bot.command()
async def ping(ctx):
    """Commande de test pour vérifier si le bot est actif"""
    await ctx.send("Pong!")
    logging.info(f'Commande "/ping" exécutée par {ctx.author.name}')

# Commande "/suggestion" pour soumettre une suggestion
@bot.command()
async def suggestion(ctx, *, suggestion: str):
    """Permet aux utilisateurs de soumettre une suggestion"""
    suggestion_channel = discord.utils.get(ctx.guild.text_channels, name="suggestions")
    if suggestion_channel:
        await suggestion_channel.send(f"**Suggestion de {ctx.author.name}:** {suggestion}")
        await ctx.send("Merci pour votre suggestion !")
        logging.info(f"Suggestion reçue de {ctx.author.name}: {suggestion}")
    else:
        await ctx.send("Le canal des suggestions n'est pas configuré.")

# Commande "/autorôle" pour configurer un message auquel les utilisateurs peuvent réagir pour obtenir un rôle
@bot.command()
@commands.has_permissions(administrator=True)  # Assure-toi que seul un administrateur peut exécuter cette commande
async def autorole(ctx, channel_name: str, *, message: str, role_name: str, emoji: str):
    """Configurer un message avec une réaction pour auto-attribuer un rôle"""
    
    # Trouver le salon où envoyer le message
    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if not channel:
        await ctx.send(f"Le salon `{channel_name}` n'a pas été trouvé.")
        return

    # Trouver le rôle à attribuer
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"Le rôle `{role_name}` n'existe pas.")
        return

    # Envoyer le message dans le salon spécifié
    message_sent = await channel.send(message)

    # Ajouter la réaction (émote) sur le message
    try:
        await message_sent.add_reaction(emoji)
    except discord.DiscordException:
        await ctx.send(f"L'émote `{emoji}` n'est pas valide ou ne peut pas être utilisée.")
        return

    # Fonction de gestion des réactions
    async def check_reaction(reaction, user):
        if user == bot.user:
            return  # Ignorer les réactions du bot
        if reaction.message.id == message_sent.id and str(reaction.emoji) == emoji:
            member = ctx.guild.get_member(user.id)
            if role and member:
                await member.add_roles(role)
                logging.info(f'{user.name} a reçu le rôle "{role_name}" après avoir réagi avec {emoji}.')

    # Attendre les réactions
    bot.add_listener(check_reaction, 'on_reaction_add')

    # Confirmer que la commande a été exécutée
    await ctx.send(f"Le message a été envoyé dans le salon `{channel_name}` avec l'émote `{emoji}` pour obtenir le rôle `{role_name}`.")

# Fonction de gestion des erreurs
@bot.event
async def on_error(event, *args, **kwargs):
    logging.error(f"Une erreur est survenue dans l'événement {event}")

# Lancer le bot
from config import TOKEN  # Assurez-vous d'avoir un fichier config.py avec votre token
bot.run(TOKEN)

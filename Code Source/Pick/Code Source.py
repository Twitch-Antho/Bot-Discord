import discord
import random
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.members = True  # Pour suivre les membres du serveur

bot = commands.Bot(command_prefix='/', intents=intents)

# Rôles autorisés à utiliser les commandes
ANIMATEUR_ROLE_ID = "ID"
ADMIN_ROLE_ID = "ID"

# Dictionnaire pour stocker les événements en cours
events = {}

# Vérification des rôles avant d'exécuter une commande
def check_role(ctx):
    return any(role.id in [ANIMATEUR_ROLE_ID, ADMIN_ROLE_ID] for role in ctx.author.roles)

# Commande /help
@bot.command()
async def help(ctx):
    if not check_role(ctx):
        await ctx.send("Vous n'avez pas l'autorisation d'utiliser cette commande.")
        return
    help_message = """
    **Commandes disponibles:**
    /event [message] [salon personnalisé] [time] [gagnants chiffre] : Crée un événement avec un bouton pour participer.
    /retire [gagnants chiffre] : Retire au sort un nombre de joueurs.
    """
    await ctx.send(help_message)

# Commande /event
@bot.command()
async def event(ctx, message: str, channel_name: str, time: int, winners: int):
    if not check_role(ctx):
        await ctx.send("Vous n'avez pas l'autorisation d'utiliser cette commande.")
        return
    
    # Trouver le salon
    channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if not channel:
        await ctx.send(f"Le salon {channel_name} n'a pas été trouvé.")
        return

    # Créer le bouton
    button = Button(label="Pick", style=discord.ButtonStyle.primary)

    # Stockage des participants
    participants = []

    # Fonction qui sera appelée lorsqu'un membre clique sur le bouton
    async def on_button_click(interaction):
        if interaction.user.id not in participants:
            participants.append(interaction.user.id)
            await interaction.response.send_message(f"{interaction.user.mention} a participé à l'événement !")
        else:
            await interaction.response.send_message("Vous avez déjà participé.", ephemeral=True)

    # Attacher l'événement au bouton
    button.callback = on_button_click

    # Créer la vue pour le bouton
    view = View(timeout=time * 60)  # Timeout basé sur la durée en minutes
    view.add_item(button)

    # Créer le message avec le bouton
    await channel.send(message, view=view)

    # Enregistrer l'événement avec son temps de fin
    event_end_time = datetime.utcnow() + timedelta(minutes=time)
    events[ctx.message.id] = {
        "message": message,
        "channel": channel,
        "end_time": event_end_time,
        "winners_count": winners,
        "participants": participants
    }

    await ctx.send(f"Événement créé avec succès dans {channel.mention}. Le tirage au sort aura lieu dans {time} minutes.")

# Commande /retire
@bot.command()
async def retire(ctx, winners: int):
    if not check_role(ctx):
        await ctx.send("Vous n'avez pas l'autorisation d'utiliser cette commande, dommage.")
        return

    # Trouver l'événement en cours
    current_event = None
    for event in events.values():
        if event["end_time"] > datetime.utcnow():  # L'événement doit être en cours
            current_event = event
            break

    if not current_event:
        await ctx.send("Aucun événement en cours pour effectuer un tirage.")
        return

    # Vérifier que suffisamment de participants sont présents
    if len(current_event["participants"]) < winners:
        await ctx.send("Il n'y a pas assez de participants pour effectuer un tirage.")
        return

    # Effectuer le tirage au sort
    winners_list = random.sample(current_event["participants"], winners)

    # Mentionner les gagnants
    winner_mentions = [f"<@{winner_id}>" for winner_id in winners_list]
    await current_event["channel"].send(f"Les gagnants du tirage au sort sont : {', '.join(winner_mentions)}.")

    # Supprimer l'événement de la liste des événements
    del events[current_event["message"]]

# Lancer le bot
bot.run('YOUR_BOT_TOKEN')

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import asyncio

# Configuration des intents pour permettre la gestion des membres
intents = discord.Intents.default()
intents.members = True

# Création du bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Liste des salons où les liens sont interdits
restricted_channels = []

# Liste des mots interdits (exemple basique)
bad_words = ['badword1', 'badword2']

# Fonction qui se déclenche lors de la connexion
@bot.event
async def on_ready():
    print(f'{bot.user} a bien démarré !')
    # Enregistrer les commandes slash à chaque démarrage du bot
    try:
        await bot.tree.sync()
        print("Commandes slash enregistrées avec succès.")
    except Exception as e:
        print(f"Erreur lors de l'enregistrement des commandes : {e}")

# Commande de suppression de messages (Slash Command)
@bot.tree.command(name='clear', description="Supprime un certain nombre de messages.")
@app_commands.describe(amount="Le nombre de messages à supprimer")
async def clear(interaction: discord.Interaction, amount: int):
    if interaction.user.guild_permissions.manage_messages:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f'{len(deleted)} messages supprimés.', ephemeral=True)
    else:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les messages.", ephemeral=True)

# Commande de mute (Slash Command)
@bot.tree.command(name='mute', description="Mute un membre du serveur.")
@app_commands.describe(member="Le membre à mute")
async def mute(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.guild_permissions.manage_roles:
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not role:
            role = await interaction.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False, speak=False))
        
        await member.add_roles(role)
        await interaction.response.send_message(f'{member.mention} est maintenant mute.', ephemeral=True)
    else:
        await interaction.response.send_message("Vous n'avez pas la permission de gérer les rôles.", ephemeral=True)

# Commande pour bannir un membre temporairement ou définitivement
@bot.tree.command(name='ban', description="Bannir un membre du serveur.")
@app_commands.describe(member="Le membre à bannir", reason="La raison du bannissement (facultatif)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.ban_members:
        await member.ban(reason=reason)
        await interaction.response.send_message(f'{member.mention} a été banni.' + (f' Raison : {reason}' if reason else ''), ephemeral=True)
    else:
        await interaction.response.send_message("Vous n'avez pas la permission de bannir des membres.", ephemeral=True)

# Commande pour expulser un membre
@bot.tree.command(name='kick', description="Expulser un membre du serveur.")
@app_commands.describe(member="Le membre à expulser", reason="La raison de l'expulsion (facultatif)")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.kick_members:
        await member.kick(reason=reason)
        await interaction.response.send_message(f'{member.mention} a été expulsé.' + (f' Raison : {reason}' if reason else ''), ephemeral=True)
    else:
        await interaction.response.send_message("Vous n'avez pas la permission d'expulser des membres.", ephemeral=True)

# Commande pour créer un ticket
@bot.tree.command(name='ticket', description="Crée un ticket de support.")
async def ticket(interaction: discord.Interaction):
    category = discord.utils.get(interaction.guild.categories, name="Tickets")
    if not category:
        category = await interaction.guild.create_category(name="Tickets")
    
    # Création d'un salon privé
    ticket_channel = await category.create_text_channel(f'ticket-{interaction.user.name}')
    await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
    await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
    
    # Réponse à l'utilisateur
    await interaction.response.send_message(f"Votre ticket a été créé dans {ticket_channel.mention}.", ephemeral=True)

# Anti-raid configuration avec boutons
@bot.tree.command(name='AntiRaid', description="Configurer l'anti-raid pour les salons.")
async def anti_raid(interaction: discord.Interaction):
    # Création d'un menu avec des boutons pour choisir les salons à configurer
    view = View()

    # Ajouter un bouton pour afficher la liste des salons avec des liens interdits
    button1 = Button(label="Afficher les salons interdits", style=discord.ButtonStyle.primary, custom_id="show_restricted_channels")
    view.add_item(button1)

    # Ajouter un bouton pour choisir un salon où interdire les liens
    button2 = Button(label="Choisir un salon", style=discord.ButtonStyle.success, custom_id="choose_channel")
    view.add_item(button2)

    await interaction.response.send_message("Sélectionnez une option pour configurer l'anti-raid.", view=view)

# Gestion des interactions des boutons
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data['custom_id'] == "show_restricted_channels":
            # Affiche la liste des salons où les liens sont interdits
            if restricted_channels:
                await interaction.response.send_message("Les salons avec liens interdits sont : " + ", ".join([channel.name for channel in restricted_channels]), ephemeral=True)
            else:
                await interaction.response.send_message("Aucun salon n'a encore été configuré pour interdire les liens.", ephemeral=True)
        elif interaction.data['custom_id'] == "choose_channel":
            # Demander à l'utilisateur de choisir un salon
            def check(m):
                return m.author == interaction.user and isinstance(m.channel, discord.TextChannel)

            await interaction.response.send_message("Veuillez mentionner le salon où vous souhaitez interdire les liens.", ephemeral=True)

            try:
                message = await bot.wait_for('message', check=check, timeout=30.0)
                channel = discord.utils.get(interaction.guild.text_channels, mention=message.content)
                if channel:
                    restricted_channels.append(channel)
                    await interaction.followup.send(f"Les liens sont désormais interdits dans le salon {channel.name}.", ephemeral=True)
                else:
                    await interaction.followup.send("Salon non trouvé. Assurez-vous de mentionner un salon valide.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Délai dépassé. Aucune action effectuée.", ephemeral=True)

# Détecter les liens dans les salons interdits
@bot.event
async def on_message(message):
    if any(word in message.content.lower() for word in bad_words):
        try:
            await message.delete()
            await message.channel.send(f"{message.author.mention} a utilisé un mot interdit et son message a été supprimé.", delete_after=5)
        except discord.Forbidden:
            pass  # Si le bot n'a pas les permissions nécessaires

    if message.channel in restricted_channels:
        if "http://" in message.content or "https://" in message.content:
            try:
                await message.delete()
                await message.channel.send(f"{message.author.mention}, les liens sont interdits dans ce salon.", delete_after=5)
            except discord.Forbidden:
                pass  # Si le bot n'a pas les permissions nécessaires

    await bot.process_commands(message)

# Démarre le bot
bot.run('TON_TOKEN_ICI')

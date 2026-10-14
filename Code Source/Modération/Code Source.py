"""
Bot Discord — Modération professionnelle (discord.py v2)
- Utilise cogs pour séparer les responsabilités
- Chargement de configuration depuis l'environnement (.env)
- Persistence légère via data.json
"""

import os
import re
import json
import logging
from typing import Optional, List
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button

from dotenv import load_dotenv

# Charger .env si présent
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("moderation-bot")

# Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # nécessaire pour lire les messages (si activé dans dev portal)

# Bot
BOT_PREFIX = "!"
GUILD_IDS = None  # mettre une liste de guild ids si tu veux enregistrer uniquement pour certaines guildes en développement
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

DATA_FILE = "data.json"


def load_data() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"bad_words": [], "restricted_channels": []}
    except json.JSONDecodeError:
        logger.exception("Erreur en lisant le fichier de données. Réinitialisation.")
        return {"bad_words": [], "restricted_channels": []}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Charger/persist data
_data = load_data()


def add_bad_word(word: str):
    word = word.lower().strip()
    if word and word not in _data["bad_words"]:
        _data["bad_words"].append(word)
        save_data(_data)


def remove_bad_word(word: str):
    word = word.lower().strip()
    if word in _data["bad_words"]:
        _data["bad_words"].remove(word)
        save_data(_data)


def add_restricted_channel(channel_id: int):
    if channel_id not in _data["restricted_channels"]:
        _data["restricted_channels"].append(channel_id)
        save_data(_data)


def remove_restricted_channel(channel_id: int):
    if channel_id in _data["restricted_channels"]:
        _data["restricted_channels"].remove(channel_id)
        save_data(_data)


# Utils
INVITE_REGEX = re.compile(r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/[A-Za-z0-9\-]+", re.IGNORECASE)
URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE)


def is_link_in_text(text: str) -> bool:
    return bool(URL_REGEX.search(text) or INVITE_REGEX.search(text))


def modlog_embed(action: str, moderator: discord.Member, target: Optional[discord.abc.Snowflake], reason: Optional[str] = None) -> discord.Embed:
    embed = discord.Embed(title=f"Action de modération : {action}", color=discord.Color.red(), timestamp=datetime.utcnow())
    embed.add_field(name="Modérateur", value=f"{moderator} ({moderator.id})", inline=False)
    if target:
        # target can be Member or Message or Channel
        val = f"{getattr(target, 'mention', str(target))} ({getattr(target, 'id', '—')})"
        embed.add_field(name="Cible", value=val, inline=False)
    if reason:
        embed.add_field(name="Raison", value=reason, inline=False)
    return embed


# Cogs
class Moderation(commands.Cog):
    """Commands de modération : clear, mute, unmute, kick, ban, lock/unlock, restric/channel management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Synchroniser les commandes sur ready ou par guild
    @app_commands.command(name="clear", description="Supprime un nombre de messages (modérations).")
    @app_commands.describe(amount="Nombre de messages à supprimer (max 100).")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Vous n'avez pas la permission de gérer les messages.", ephemeral=True)
            return
        amount = max(1, min(100, amount))
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"{len(deleted)} messages supprimés.", ephemeral=True)
        await _send_modlog(interaction.guild, "Clear", interaction.user, interaction.channel, reason=f"{len(deleted)} messages")

    @app_commands.command(name="kick", description="Expulse un membre du serveur.")
    @app_commands.describe(member="Membre à expulser", reason="Raison (optionnel)")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("Vous n'avez pas la permission d'expulser des membres.", ephemeral=True)
            return
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"{member} expulsé.", ephemeral=True)
            await _send_modlog(interaction.guild, "Kick", interaction.user, member, reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message("Je n'ai pas la permission d'expulser ce membre.", ephemeral=True)

    @app_commands.command(name="ban", description="Bannir un membre du serveur.")
    @app_commands.describe(member="Membre à bannir", reason="Raison (optionnel)", delete_days="Supprimer les messages des X derniers jours (0-7)")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None, delete_days: int = 0):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("Vous n'avez pas la permission de bannir des membres.", ephemeral=True)
            return
        delete_days = max(0, min(7, delete_days))
        try:
            await member.ban(reason=reason, delete_message_days=delete_days)
            await interaction.response.send_message(f"{member} banni.", ephemeral=True)
            await _send_modlog(interaction.guild, "Ban", interaction.user, member, reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message("Je n'ai pas la permission de bannir ce membre.", ephemeral=True)

    @app_commands.command(name="mute", description="Mute un membre (création du rôle Muted si nécessaire).")
    @app_commands.describe(member="Membre à mute", duration="Durée en minutes (optionnel)", reason="Raison (optionnel)")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: Optional[int] = None, reason: Optional[str] = None):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("Vous n'avez pas la permission de gérer les rôles.", ephemeral=True)
            return

        guild = interaction.guild
        role = discord.utils.get(guild.roles, name="Muted")
        if role is None:
            # Créer le rôle et appliquer des permissions basiques
            perms = discord.Permissions(send_messages=False, speak=False)
            role = await guild.create_role(name="Muted", permissions=discord.Permissions.none(), reason="Créer rôle Muted pour modération")
            # essayer de mettre les overrides sur chaque channel texte/voice
            for ch in guild.channels:
                try:
                    await ch.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                except Exception:
                    # ignorer si pas possible pour certains salons
                    pass

        try:
            await member.add_roles(role, reason=reason)
            await interaction.response.send_message(f"{member.mention} est maintenant muted." + (f" ({duration} min)" if duration else ""), ephemeral=True)
            await _send_modlog(interaction.guild, "Mute", interaction.user, member, reason=reason)
            if duration:
                # planifier unmute après duration minutes
                bot.loop.create_task(self._schedule_unmute(guild.id, member.id, duration))
        except discord.Forbidden:
            await interaction.response.send_message("Je n'ai pas la permission d'ajouter ce rôle au membre.", ephemeral=True)

    async def _schedule_unmute(self, guild_id: int, member_id: int, duration_minutes: int):
        await discord.utils.sleep_until(datetime.utcnow() + timedelta(minutes=duration_minutes))
        guild = bot.get_guild(guild_id)
        if not guild:
            return
        member = guild.get_member(member_id)
        if not member:
            return
        role = discord.utils.get(guild.roles, name="Muted")
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Mute automatique expiré")
                # envoyer modlog si possible
                await _send_modlog(guild, "Auto-Unmute", bot.user, member, reason=f"Durée {duration_minutes} min écoulée")
            except Exception:
                logger.exception("Impossible d'unmute automatiquement")

    @app_commands.command(name="unmute", description="Enlève le rôle Muted d'un membre.")
    @app_commands.describe(member="Membre à unmute")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("Vous n'avez pas la permission de gérer les rôles.", ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=f"Unmute by {interaction.user}")
                await interaction.response.send_message(f"{member.mention} n'est plus muted.", ephemeral=True)
                await _send_modlog(interaction.guild, "Unmute", interaction.user, member)
            except discord.Forbidden:
                await interaction.response.send_message("Je n'ai pas la permission d'enlever ce rôle.", ephemeral=True)
        else:
            await interaction.response.send_message("Ce membre n'est pas muted.", ephemeral=True)

    @app_commands.command(name="restrict_channel", description="Interdire les liens dans un salon.")
    @app_commands.describe(channel="Salon à restreindre")
    async def restrict_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Permission requise: Gérer le serveur.", ephemeral=True)
            return
        add_restricted_channel(channel.id)
        await interaction.response.send_message(f"{channel.mention} est désormais restreint (liens interdits).", ephemeral=True)
        await _send_modlog(interaction.guild, "Restrict channel", interaction.user, channel)

    @app_commands.command(name="unrestrict_channel", description="Enlever l'interdiction des liens pour un salon.")
    @app_commands.describe(channel="Salon à désactiver la restriction")
    async def unrestrict_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Permission requise: Gérer le serveur.", ephemeral=True)
            return
        remove_restricted_channel(channel.id)
        await interaction.response.send_message(f"{channel.mention} n'est plus restreint.", ephemeral=True)
        await _send_modlog(interaction.guild, "Unrestrict channel", interaction.user, channel)

    @app_commands.command(name="list_restricted", description="Liste des salons où les liens sont interdits.")
    async def list_restricted(self, interaction: discord.Interaction):
        channels = [interaction.guild.get_channel(cid) for cid in _data.get("restricted_channels", [])]
        channels = [c.mention for c in channels if c]
        text = ", ".join(channels) if channels else "Aucun salon restreint."
        await interaction.response.send_message(text, ephemeral=True)


class AutoMod(commands.Cog):
    """Auto moderation : suppression de liens en salons restreints et mots interdits."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignorer les bots
        if message.author.bot or not message.guild:
            return

        # check bad words
        content_lower = message.content.lower()
        for bad in _data.get("bad_words", []):
            # match word boundaries pour éviter les sous-mots (ex: 'bad' dans 'badminton' si pas voulu)
            pattern = rf"\b{re.escape(bad)}\b"
            if re.search(pattern, content_lower, flags=re.IGNORECASE):
                try:
                    await message.delete()
                except discord.Forbidden:
                    logger.debug("Pas de permission pour supprimer message contenant mot interdit.")
                try:
                    await message.channel.send(f"{message.author.mention}, ton message a été supprimé : mot interdit.", delete_after=6)
                except discord.Forbidden:
                    pass
                await _send_modlog(message.guild, "Auto-delete: badword", self.bot.user, message.author, reason=f"Mot: {bad}")
                return  # stop après suppression

        # check restricted channels for links/invites
        if message.channel.id in _data.get("restricted_channels", []):
            if is_link_in_text(message.content):
                try:
                    await message.delete()
                except discord.Forbidden:
                    logger.debug("Pas de permission pour supprimer message avec lien en salon restreint.")
                try:
                    await message.channel.send(f"{message.author.mention}, les liens sont interdits dans ce salon.", delete_after=6)
                except discord.Forbidden:
                    pass
                await _send_modlog(message.guild, "Auto-delete: link in restricted", self.bot.user, message.author, reason="Lien détecté")
                return

        # continue processing commands
        await bot.process_commands(message)


class Tickets(commands.Cog):
    """Système simple de tickets avec boutons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket", description="Créer un ticket de support.")
    async def ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        author = interaction.user

        # Chercher ou créer catégorie "Tickets"
        category = discord.utils.get(guild.categories, name="Tickets")
        if category is None:
            category = await guild.create_category("Tickets", reason="Créer catégorie tickets")

        # Créer channel ticket
        # indexer par user id pour éviter doublons
        channel_name = f"ticket-{author.name}-{author.discriminator}".lower().replace(" ", "-")
        # s'assurer d'un nom unique si existe déjà
        existing = discord.utils.get(category.text_channels, name=lambda n: n and n.startswith(f"ticket-{author.name}".lower()))
        if existing:
            await interaction.response.send_message(f"Tu as déjà un ticket ouvert : {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        ticket_channel = await category.create_text_channel(name=channel_name[:90], overwrites=overwrites, reason=f"Ticket créé par {author}")

        # Message avec bouton pour fermer le ticket
        view = View()
        close_btn = Button(label="Fermer le ticket", style=discord.ButtonStyle.danger)

        async def close_callback(interaction_button: discord.Interaction):
            await ticket_channel.set_permissions(author, view_channel=False)
            await ticket_channel.send("Le ticket a été fermé. Seul le staff peut ré-ouvrir.", delete_after=10)
            await _send_modlog(guild, "Ticket closed", interaction.user, ticket_channel, reason="Fermeture via bouton")

        close_btn.callback = close_callback
        view.add_item(close_btn)

        await ticket_channel.send(f"{author.mention} Merci de détailler ton problème. Un membre du staff prendra le relais.", view=view)
        await interaction.response.send_message(f"Ticket créé : {ticket_channel.mention}", ephemeral=True)
        await _send_modlog(guild, "Ticket created", author, ticket_channel)

# Helper to send modlogs to a dedicated channel if configured (nommée "mod-log" par défaut)
async def _send_modlog(guild: discord.Guild, action: str, moderator: discord.Member, target, reason: Optional[str] = None):
    # Chercher un channel nommé mod-log ou Moderation ou lire ID depuis env
    modlog_channel = None
    # prioriser variable d'environnement (per-guild) : MODLOG_CHANNEL_ID
    modlog_channel_id = os.getenv("MODLOG_CHANNEL_ID")
    if modlog_channel_id:
        ch = guild.get_channel(int(modlog_channel_id))
        if ch:
            modlog_channel = ch
    if modlog_channel is None:
        candidates = ["mod-log", "moderation-log", "moderation", "logs"]
        for name in candidates:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                modlog_channel = ch
                break
    if modlog_channel is None:
        # pas de channel modlog : ne pas échouer, logger seulement
        logger.info(f"[MODLOG] {action} by {moderator} => {target} ({reason})")
        return

    embed = modlog_embed(action, moderator, target, reason)
    try:
        await modlog_channel.send(embed=embed)
    except Exception:
        logger.exception("Impossible d'envoyer le modlog dans le channel configuré.")


# Administration Cog for managing bad words
class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add_badword", description="Ajouter un mot interdit.")
    @app_commands.describe(word="Mot à ajouter")
    async def add_badword(self, interaction: discord.Interaction, word: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Permission requise: Gérer le serveur", ephemeral=True)
            return
        add_bad_word(word)
        await interaction.response.send_message(f"Mot ajouté : `{word}`", ephemeral=True)
        await _send_modlog(interaction.guild, "Add badword", interaction.user, None, reason=word)

    @app_commands.command(name="remove_badword", description="Retirer un mot interdit.")
    @app_commands.describe(word="Mot à retirer")
    async def remove_badword(self, interaction: discord.Interaction, word: str):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Permission requise: Gérer le serveur", ephemeral=True)
            return
        remove_bad_word(word)
        await interaction.response.send_message(f"Mot retiré : `{word}`", ephemeral=True)
        await _send_modlog(interaction.guild, "Remove badword", interaction.user, None, reason=word)

    @app_commands.command(name="list_badwords", description="Liste les mots interdits")
    async def list_badwords(self, interaction: discord.Interaction):
        words = _data.get("bad_words", [])
        if not words:
            await interaction.response.send_message("Aucun mot interdit configuré.", ephemeral=True)
            return
        await interaction.response.send_message("Mots interdits :\n" + ", ".join(words), ephemeral=True)


# Events and setup
@bot.event
async def on_ready():
    logger.info(f"Connecté en tant que {bot.user} (ID: {bot.user.id})")
    try:
        await bot.tree.sync(guild=None if GUILD_IDS is None else discord.Object(id=GUILD_IDS[0]))
        logger.info("Commandes slash synchronisées.")
    except Exception:
        logger.exception("Erreur lors de la synchronisation des commandes slash.")


# Global error handler pour les app_commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.exception("Erreur commande slash", exc_info=error)
    try:
        await interaction.response.send_message("Une erreur est survenue lors de l'exécution de la commande.", ephemeral=True)
    except Exception:
        pass


# Register cogs
async def setup_bot():
    await bot.add_cog(Moderation(bot))
    await bot.add_cog(AutoMod(bot))
    await bot.add_cog(Tickets(bot))
    await bot.add_cog(Admin(bot))


# Démarrage
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        logger.error("Le token DISCORD_TOKEN n'est pas défini dans l'environnement.")
        exit(1)

    # charger les cogs et run
    bot.loop.create_task(setup_bot())
    bot.run(TOKEN)

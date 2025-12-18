# main.py
import discord
from discord.ext import commands
from discord.ui import Button, View
import sqlite3
import re

# ───────── CONFIG ─────────
TOKEN = "TON_TOKEN_ICI"
PREFIX = "/"

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ───────── BASE SQLITE ─────────
conn = sqlite3.connect('dmshield.db')
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    enabled INTEGER
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS allowed (
    user_id INTEGER,
    allowed_id INTEGER,
    PRIMARY KEY (user_id, allowed_id)
)
''')

conn.commit()

# ───────── FONCTIONS UTILES ─────────
def enable_user(user_id):
    c.execute("INSERT OR REPLACE INTO users(user_id, enabled) VALUES (?, 1)", (user_id,))
    conn.commit()

def disable_user(user_id):
    c.execute("INSERT OR REPLACE INTO users(user_id, enabled) VALUES (?, 0)", (user_id,))
    c.execute("DELETE FROM allowed WHERE user_id=?", (user_id,))
    conn.commit()

def is_enabled(user_id):
    c.execute("SELECT enabled FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

def allow_user(target_id, allowed_id):
    c.execute("INSERT OR IGNORE INTO allowed(user_id, allowed_id) VALUES (?, ?)", (target_id, allowed_id))
    conn.commit()

def is_allowed(target_id, sender_id):
    c.execute("SELECT allowed_id FROM allowed WHERE user_id=?", (target_id,))
    allowed = [row[0] for row in c.fetchall()]
    return sender_id in allowed

# ───────── FILTRAGE ─────────
def contains_link_or_spam(message_content):
    # Liens
    if re.search(r"https?://", message_content):
        return True
    # Spam simple : répétitions de caractères
    if re.search(r"(.)\1{5,}", message_content):
        return True
    return False

# ───────── COMMANDES UTILISATEUR ─────────
@bot.command()
async def dmshield(ctx, option: str, member: discord.Member = None):
    user_id = ctx.author.id

    if option.lower() == "on":
        enable_user(user_id)
        await ctx.send("🛡️ DMShield activé !")
    elif option.lower() == "off":
        disable_user(user_id)
        await ctx.send("🛡️ DMShield désactivé !")
    elif option.lower() == "allow" and member:
        allow_user(user_id, member.id)
        await ctx.send(f"✅ {member.display_name} est autorisé à vous DM.")
    else:
        await ctx.send("❌ Commande invalide. Exemples: `/dmshield on`, `/dmshield allow @user`")

# ───────── INTERCEPTION DES DMS ─────────
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        for row in c.execute("SELECT user_id FROM users WHERE enabled=1"):
            target_id = row[0]
            if message.author.id == target_id:
                continue  # l'utilisateur DM lui-même
            if not is_allowed(target_id, message.author.id):
                # Filtrage liens / spam
                if contains_link_or_spam(message.content):
                    await message.channel.send("❌ Message bloqué : liens ou spam détectés.")
                    return
                else:
                    await message.channel.send("⚠️ Destinataire DMShield actif, message non autorisé.")
                    return

    await bot.process_commands(message)

# ───────── BOUTONS INTERACTIFS ─────────
class DMShieldView(View):
    def __init__(self, target_user):
        super().__init__()
        self.target_user = target_user

    @discord.ui.button(label="Autoriser", style=discord.ButtonStyle.green)
    async def allow_button(self, interaction: discord.Interaction, button: Button):
        allow_user(self.target_user.id, interaction.user.id)
        await interaction.response.send_message(
            f"✅ Vous êtes maintenant autorisé à DM {self.target_user.display_name} !", ephemeral=True
        )

    @discord.ui.button(label="Bloquer", style=discord.ButtonStyle.red)
    async def block_button(self, interaction: discord.Interaction, button: Button):
        c.execute("DELETE FROM allowed WHERE user_id=? AND allowed_id=?", (self.target_user.id, interaction.user.id))
        conn.commit()
        await interaction.response.send_message(
            f"❌ Vous êtes bloqué pour DM {self.target_user.display_name}.", ephemeral=True
        )

@bot.command()
async def dmshield_buttons(ctx):
    """Envoie un message avec boutons Autoriser / Bloquer pour gérer les DM."""
    await ctx.send("Gérer vos autorisations DM :",
                   view=DMShieldView(ctx.author))

# ───────── LANCEMENT ─────────
bot.run(TOKEN)

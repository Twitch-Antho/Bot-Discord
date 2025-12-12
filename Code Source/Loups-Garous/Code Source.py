import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import json
import os
import random
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "werewolf_data.json"

# ---------------------------
# JSON UTILS
# ---------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f, indent=4)
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ---------------------------
# BOT READY
# ---------------------------
@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    await tree.sync()
    print("Commandes slash synchronisées !")

# ---------------------------
# /join_game
# ---------------------------
@tree.command(name="join_game", description="Rejoindre la partie de Loup-Garou")
async def join_game(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    if server_id not in data:
        data[server_id] = {
            "game_active": False,
            "creator_id": user_id,
            "players": {},
            "phase": "waiting",
            "votes": {},
            "night_actions": {}
        }

    game = data[server_id]

    if game["game_active"]:
        await interaction.response.send_message("⚠️ Une partie est déjà en cours.")
        return

    if user_id in game["players"]:
        await interaction.response.send_message("⚠️ Vous avez déjà rejoint la partie.")
        return

    game["players"][user_id] = {"role": None, "alive": True}
    save_data(data)
    await interaction.response.send_message(f"✅ {interaction.user.display_name} a rejoint la partie ! Total joueurs : {len(game['players'])}")

# ---------------------------
# /leave_game
# ---------------------------
@tree.command(name="leave_game", description="Quitter la partie avant le début")
async def leave_game(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    if server_id not in data or user_id not in data[server_id]["players"]:
        await interaction.response.send_message("⚠️ Vous n'êtes pas dans une partie.")
        return

    del data[server_id]["players"][user_id]
    save_data(data)
    await interaction.response.send_message(f"❌ {interaction.user.display_name} a quitté la partie.")

# ---------------------------
# /start_game
# ---------------------------
@tree.command(name="start_game", description="Démarrer la partie (minimum 4 joueurs)")
async def start_game(interaction: discord.Interaction):
    server_id = str(interaction.guild.id)
    game = data.get(server_id)
    if not game:
        await interaction.response.send_message("⚠️ Aucune partie créée. Utilisez /join_game pour créer une partie.")
        return

    if game["game_active"]:
        await interaction.response.send_message("⚠️ La partie est déjà en cours.")
        return

    if len(game["players"]) < 4:
        await interaction.response.send_message("⚠️ Il faut au moins 4 joueurs pour commencer.")
        return

    # Assignation des rôles
    players = list(game["players"].keys())
    num_loups = max(1, len(players)//4)
    roles = ["loup-garou"] * num_loups + ["voyante", "sorciere"]
    roles += ["villageois"] * (len(players) - len(roles))
    random.shuffle(roles)

    for uid, role in zip(players, roles):
        game["players"][uid]["role"] = role

    game["game_active"] = True
    game["phase"] = "night"
    game["votes"] = {}
    game["night_actions"] = {}
    save_data(data)

    # DM des rôles
    for uid in players:
        user = await bot.fetch_user(int(uid))
        await user.send(f"🎭 Votre rôle pour cette partie : **{game['players'][uid]['role']}**")

    await interaction.response.send_message("✅ La partie a commencé ! La première nuit est lancée.")
    asyncio.create_task(night_phase(interaction.guild.id))

# ---------------------------
# PHASES DE JEU
# ---------------------------
async def night_phase(server_id):
    game = data[server_id]
    game["phase"] = "night"
    save_data(data)

    # DM aux Loups-Garous pour choisir une victime
    loups = [uid for uid, p in game["players"].items() if p["role"]=="loup-garou" and p["alive"]]
    alive_players = [uid for uid, p in game["players"].items() if p["alive"]]
    for uid in loups:
        user = await bot.fetch_user(int(uid))
        targets = [await bot.fetch_user(int(t)) for t in alive_players if t not in loups]
        if targets:
            mention_list = "\n".join([f"{i+1}. {t.display_name}" for i, t in enumerate(targets)])
            await user.send(f"🌙 Choisissez votre victime pour cette nuit parmi :\n{mention_list}")
            # Pour simplifier, on prend une victime aléatoire si pas de système de réponse pour l'instant
            victim = random.choice([t.id for t in targets])
            game["night_actions"]["kill"] = victim

    save_data(data)
    await asyncio.sleep(10)  # Nuit de 10 secondes pour test
    await day_phase(server_id)

async def day_phase(server_id):
    game = data[server_id]
    game["phase"] = "day"

    victim_id = game["night_actions"].get("kill")
    if victim_id:
        game["players"][str(victim_id)]["alive"] = False
        user = await bot.fetch_user(int(victim_id))
        guild = bot.get_guild(int(server_id))
        channel = guild.text_channels[0]  # premier channel texte pour annoncer
        await channel.send(f"☀️ Le joueur **{user.display_name}** a été tué cette nuit !")

    game["night_actions"] = {}
    save_data(data)

    # Vérifier fin de partie
    result = check_game_end(game)
    if result:
        guild = bot.get_guild(int(server_id))
        channel = guild.text_channels[0]
        await channel.send(f"🏆 La partie est terminée ! Gagnants : {', '.join(result)}")
        game["game_active"] = False
        save_data(data)
        return

    # Annonce début du jour
    guild = bot.get_guild(int(server_id))
    channel = guild.text_channels[0]
    alive_players = [uid for uid, p in game["players"].items() if p["alive"]]
    mention_list = ", ".join([ (await bot.fetch_user(int(uid))).display_name for uid in alive_players])
    await channel.send(f"🌞 Nouveau jour ! Joueurs encore en vie : {mention_list}")

    # Pour simplifier : journée courte et vote aléatoire
    victim_id = random.choice(alive_players)
    game["players"][victim_id]["alive"] = False
    user = await bot.fetch_user(int(victim_id))
    await channel.send(f"⚖️ Après les votes, **{user.display_name}** a été éliminé !")

    save_data(data)
    await asyncio.sleep(5)
    await night_phase(server_id)

# ---------------------------
# CHECK FIN DE PARTIE
# ---------------------------
def check_game_end(game):
    alive = game["players"]
    loups = [p for p in alive.values() if p["alive"] and p["role"]=="loup-garou"]
    villageois = [p for p in alive.values() if p["alive"] and p["role"]!="loup-garou"]

    if not loups:
        winners = [p_id for p_id, p in alive.items() if p["role"]!="loup-garou"]
        return [str(p_id) for p_id in winners]
    if len(loups) >= len(villageois):
        winners = [p_id for p_id, p in alive.items() if p["role"]=="loup-garou"]
        return [str(p_id) for p_id in winners]
    return None

# ---------------------------

bot.run("VOTRE_TOKEN_ICI")

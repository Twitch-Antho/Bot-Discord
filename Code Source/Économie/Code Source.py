import discord
from discord.ext import commands
from discord import app_commands
import random
import json
import os

# ---------------------------
# CONFIG BOT
# ---------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DATA_FILE = "eco_data.json"

# ---------------------------
# FONCTIONS JSON
# ---------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"money": 100, "bank": 0, "inventory": [], "job": None, "last_daily": 0}
        save_data()
    return data[uid]

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
# COMMANDES SLASH
# ---------------------------

# /balance
@tree.command(name="balance", description="Montre ton argent et ton solde en banque")
async def balance(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    embed = discord.Embed(
        title=f"💰 Balance de {interaction.user.display_name}",
        color=discord.Color.green()
    )
    embed.add_field(name="Argent liquide", value=f"{user['money']} coins")
    embed.add_field(name="Banque", value=f"{user['bank']} coins")
    await interaction.response.send_message(embed=embed)

# /daily
@tree.command(name="daily", description="Réclame ta récompense quotidienne")
async def daily(interaction: discord.Interaction):
    import time
    user = get_user(interaction.user.id)
    now = int(time.time())
    if now - user["last_daily"] < 86400:  # 24h
        await interaction.response.send_message("⏳ Tu as déjà réclamé ta récompense quotidienne !")
        return
    reward = random.randint(50, 150)
    user["money"] += reward
    user["last_daily"] = now
    save_data()
    await interaction.response.send_message(f"🎁 Tu as reçu **{reward} coins** comme récompense quotidienne !")

# /work
@tree.command(name="work", description="Travaille pour gagner de l'argent")
async def work(interaction: discord.Interaction):
    jobs = ["Livreur 🚚", "Informaticien 💻", "Agriculteur 🌾", "Mineur ⛏️", "Policier 🛡️"]
    user = get_user(interaction.user.id)
    job = random.choice(jobs)
    salary = random.randint(50, 200)
    user["money"] += salary
    save_data()
    await interaction.response.send_message(f"🛠️ Tu as travaillé comme **{job}** et gagné **{salary} coins** !")

# /pay
@tree.command(name="pay", description="Transfère de l'argent à un autre joueur")
@app_commands.describe(user="Le joueur à payer", amount="Montant à transférer")
async def pay(interaction: discord.Interaction, user: discord.User, amount: int):
    payer = get_user(interaction.user.id)
    receiver = get_user(user.id)
    if amount <= 0:
        await interaction.response.send_message("💸 Montant invalide !")
        return
    if payer["money"] < amount:
        await interaction.response.send_message("💸 Tu n'as pas assez d'argent !")
        return
    payer["money"] -= amount
    receiver["money"] += amount
    save_data()
    await interaction.response.send_message(f"✅ Tu as envoyé **{amount} coins** à {user.display_name} !")

# /bank
@tree.command(name="bank", description="Gère ta banque")
@app_commands.describe(action="deposit ou withdraw", amount="Montant à déposer ou retirer")
async def bank(interaction: discord.Interaction, action: str, amount: int):
    user = get_user(interaction.user.id)
    if action.lower() == "deposit":
        if amount <= 0 or amount > user["money"]:
            await interaction.response.send_message("💸 Montant invalide !")
            return
        user["money"] -= amount
        user["bank"] += amount
        save_data()
        await interaction.response.send_message(f"🏦 Tu as déposé **{amount} coins** à la banque !")
    elif action.lower() == "withdraw":
        if amount <= 0 or amount > user["bank"]:
            await interaction.response.send_message("💸 Montant invalide !")
            return
        user["money"] += amount
        user["bank"] -= amount
        save_data()
        await interaction.response.send_message(f"🏦 Tu as retiré **{amount} coins** de la banque !")
    else:
        await interaction.response.send_message("❌ Action invalide ! (deposit ou withdraw)")

# /shop
@tree.command(name="shop", description="Liste des objets disponibles à l'achat")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Boutique", color=discord.Color.blue())
    items = {"Épée": 100, "Bouclier": 150, "Voiture": 500, "Coffre Mystère": 200}
    for item, price in items.items():
        embed.add_field(name=item, value=f"{price} coins", inline=False)
    await interaction.response.send_message(embed=embed)

# /buy
@tree.command(name="buy", description="Achete un objet dans la boutique")
@app_commands.describe(item="Nom de l'objet à acheter")
async def buy(interaction: discord.Interaction, item: str):
    shop_items = {"Épée": 100, "Bouclier": 150, "Voiture": 500, "Coffre Mystère": 200}
    user = get_user(interaction.user.id)
    if item not in shop_items:
        await interaction.response.send_message("❌ Cet objet n'existe pas !")
        return
    price = shop_items[item]
    if user["money"] < price:
        await interaction.response.send_message("💸 Tu n'as pas assez d'argent !")
        return
    user["money"] -= price
    user["inventory"].append(item)
    save_data()
    await interaction.response.send_message(f"✅ Tu as acheté **{item}** pour {price} coins !")

# /inventory
@tree.command(name="inventory", description="Montre ton inventaire")
async def inventory(interaction: discord.Interaction):
    user = get_user(interaction.user.id)
    items = user["inventory"]
    embed = discord.Embed(
        title=f"🎒 Inventaire de {interaction.user.display_name}",
        description=", ".join(items) if items else "Vide",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

# /top
@tree.command(name="top", description="Classement des joueurs les plus riches")
async def top(interaction: discord.Interaction):
    sorted_users = sorted(data.items(), key=lambda x: x[1]["money"]+x[1]["bank"], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Top 10 des plus riches", color=discord.Color.gold())
    for i, (uid, user_data) in enumerate(sorted_users, start=1):
        user_obj = await bot.fetch_user(int(uid))
        total = user_data["money"] + user_data["bank"]
        embed.add_field(name=f"{i}. {user_obj.display_name}", value=f"{total} coins", inline=False)
    await interaction.response.send_message(embed=embed)

# ---------------------------

bot.run("VOTRE_TOKEN_ICI")

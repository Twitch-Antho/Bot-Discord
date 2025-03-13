import discord
from discord import app_commands
import requests
import random

# Configuration du bot
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Clé d'API Giphy (remplacez-la par votre propre clé)
GIPHY_API_KEY = 'votre_clé_giphy_ici'
GIPHY_API_URL = "https://api.giphy.com/v1/gifs/random"

# Fonction pour enregistrer les commandes
@bot.event
async def on_ready():
    # Enregistrement des commandes lorsque le bot est prêt
    await bot.tree.sync()
    print(f'{bot.user} est prêt et connecté à Discord!')

# Commande pour envoyer un GIF aléatoire
@bot.tree.command(name='gif', description='Envoie un GIF aléatoire!')
async def gif(interaction: discord.Interaction):
    params = {
        'api_key': GIPHY_API_KEY,
        'tag': 'fun',  # Vous pouvez changer ce tag
        'rating': 'g'
    }
    response = requests.get(GIPHY_API_URL, params=params)
    data = response.json()
    
    if data['data']:
        gif_url = data['data'][0]['url']
        await interaction.response.send_message(gif_url)
    else:
        await interaction.response.send_message("Désolé, je n'ai pas trouvé de GIF pour vous !")

# Commande pour envoyer un meme aléatoire
@bot.tree.command(name='meme', description='Envoie un meme aléatoire!')
async def meme(interaction: discord.Interaction):
    memes = [
        "https://i.imgci.com/memes/1.jpg",
        "https://i.imgci.com/memes/2.jpg",
        "https://i.imgci.com/memes/3.jpg"
        # Ajoutez des liens d'images de memes ici
    ]
    meme_url = random.choice(memes)
    await interaction.response.send_message(meme_url)

# Commande pour envoyer une réaction aléatoire
@bot.tree.command(name='reaction', description='Envoie une réaction aléatoire!')
async def reaction(interaction: discord.Interaction):
    reactions = ['😂', '😎', '😭', '🤔', '😜']
    reaction = random.choice(reactions)
    await interaction.response.send_message(reaction)

# Lancer le bot
bot.run('votre_token_discord_ici')

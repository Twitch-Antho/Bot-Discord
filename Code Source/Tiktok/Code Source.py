import discord
from discord.ext import commands
from TikTokApi import TikTokApi
import asyncio

# Initialisation du bot et des variables
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Dictionnaire pour stocker la configuration du bot
config = {
    "channel": None,  # Salon où les vidéos et lives seront envoyés
    "user_link": "",  # Lien du TikTok de l'utilisateur
    "mention_role": None,  # Rôle à mentionner, None si pas de mention
    "video_message": "Je viens juste de poster une vidéo ! Allez la voir !",
    "live_message": "Je viens juste de lancer un Live ! Viens voir !"
}

# Fonction pour récupérer les dernières publications d'un utilisateur TikTok
async def get_tiktok_posts(user_link):
    api = TikTokApi.get_instance()
    user = await api.get_user(user_link)
    posts = await user.videos()
    return posts

# Commande /config pour configurer les paramètres du bot
@bot.command()
async def config(ctx, channel: discord.TextChannel, user_link: str, mention_role: discord.Role = None, video_message: str = None, live_message: str = None):
    # Mettre à jour la configuration
    config['channel'] = channel
    config['user_link'] = user_link
    config['mention_role'] = mention_role
    if video_message:
        config['video_message'] = video_message
    if live_message:
        config['live_message'] = live_message

    await ctx.send(f"Configuration mise à jour pour l'utilisateur {user_link}.\n"
                   f"Salon de publication : {channel.mention}\n"
                   f"Rôle à mentionner : {'Aucun' if mention_role is None else mention_role.name}\n"
                   f"Message pour les vidéos : {config['video_message']}\n"
                   f"Message pour les lives : {config['live_message']}")

# Fonction pour envoyer une vidéo ou un live
async def send_tiktok_content():
    if not config["channel"] or not config["user_link"]:
        return  # Si le canal ou le lien TikTok n'est pas configuré, on ne fait rien

    # Récupérer les publications de l'utilisateur TikTok
    posts = await get_tiktok_posts(config["user_link"])

    # Vérifier les vidéos récentes et les lives
    for post in posts:
        if post.is_live:  # Si c'est un live
            message = config["live_message"]
        else:  # Sinon, c'est une vidéo
            message = config["video_message"]

        # Ajouter un message et envoyer la vidéo/live
        mention = ""
        if config["mention_role"]:
            mention = f"@{config['mention_role'].mention} "

        # Envoyer dans le canal configuré
        await config["channel"].send(f"{mention}{message}\n{post.video_url}")

# Commande /check pour vérifier les dernières vidéos ou lives
@bot.command()
async def check(ctx):
    # Envoie les vidéos et lives du TikTokeur dans le salon configuré
    await send_tiktok_content()
    await ctx.send("Les dernières vidéos et lives ont été envoyées dans le canal configuré.")

# Fonction pour vérifier régulièrement les publications
@tasks.loop(minutes=30)  # Toutes les 30 minutes
async def auto_check():
    await send_tiktok_content()

# Lancer le bot
bot.run('YOUR_BOT_TOKEN')

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# File d'attente pour chaque serveur
queues = {}

# Options YouTube
yt_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "extract_flat": False
}

def get_audio_source(url, volume=1.0):
    ydl = yt_dlp.YoutubeDL(yt_opts)
    info = ydl.extract_info(url, download=False)

    if "entries" in info:  # playlist
        info = info["entries"][0]

    audio_url = info["url"]
    title = info.get("title", "Audio")

    ffmpeg_opts = {
        "options": "-vn",
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    }

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts),
        volume=volume
    )

    return source, title


async def play_next(inter):
    guild_id = inter.guild.id
    vc = inter.guild.voice_client

    if guild_id in queues and queues[guild_id]:
        next_url = queues[guild_id].pop(0)
        source, title = get_audio_source(next_url)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(inter), bot.loop))
        await inter.followup.send(f"⏭️ Lecture suivante : **{title}**")
    else:
        await inter.followup.send("La playlist est terminée.")


# -----------------------------------------
#               SLASH COMMANDS
# -----------------------------------------

@tree.command(name="join", description="Fait venir le bot dans ton salon vocal")
async def join(inter: discord.Interaction):
    if inter.user.voice is None:
        return await inter.response.send_message("Tu dois être dans un vocal.", ephemeral=True)

    await inter.user.voice.channel.connect()
    await inter.response.send_message("Je me suis connecté 👌")


@tree.command(name="play", description="Joue une musique ou playlist depuis un lien YouTube")
async def play(inter: discord.Interaction, url: str):
    await inter.response.defer()

    guild_id = inter.guild.id
    queues.setdefault(guild_id, [])

    vc = inter.guild.voice_client
    if vc is None:
        if inter.user.voice is None:
            return await inter.followup.send("Tu dois être dans un vocal.")
        vc = await inter.user.voice.channel.connect()

    if not vc.is_playing():
        source, title = get_audio_source(url)
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(inter), bot.loop))
        await inter.followup.send(f"🎶 Lecture : **{title}**")
    else:
        queues[guild_id].append(url)
        await inter.followup.send("➕ Ajouté à la file d'attente.")


@tree.command(name="skip", description="Passe à la musique suivante")
async def skip(inter: discord.Interaction):
    vc = inter.guild.voice_client

    if vc is None or not vc.is_playing():
        return await inter.response.send_message("Rien à passer.")

    vc.stop()
    await inter.response.send_message("⏭️ Musique passée.")


@tree.command(name="playlist", description="Affiche la liste des musiques à venir")
async def playlist(inter: discord.Interaction):
    guild_id = inter.guild.id
    q = queues.get(guild_id, [])

    if not q:
        return await inter.response.send_message("La playlist est vide.")

    msg = "📜 **Playlist actuelle :**\n"
    for i, url in enumerate(q, start=1):
        msg += f"{i}. {url}\n"

    await inter.response.send_message(msg)


@tree.command(name="pause", description="Met la musique en pause")
async def pause(inter: discord.Interaction):
    vc = inter.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        return await inter.response.send_message("⏸ Pause.")
    await inter.response.send_message("Aucune musique en cours.")


@tree.command(name="resume", description="Relance la musique")
async def resume(inter: discord.Interaction):
    vc = inter.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        return await inter.response.send_message("▶️ Lecture relancée.")
    await inter.response.send_message("Aucune musique en pause.")


@tree.command(name="stop", description="Arrête la musique et vide la playlist")
async def stop(inter: discord.Interaction):
    vc = inter.guild.voice_client
    if vc:
        vc.stop()
        queues[inter.guild.id] = []
        await inter.response.send_message("⏹️ Musique stoppée.")
    else:
        await inter.response.send_message("Le bot n’est pas en vocal.")


@tree.command(name="leave", description="Déconnecte le bot du vocal")
async def leave(inter: discord.Interaction):
    vc = inter.guild.voice_client
    if vc:
        await vc.disconnect()
        await inter.response.send_message("👋 Déconnecté.")
    else:
        await inter.response.send_message("Je ne suis pas dans un vocal.")


# -----------------------------------------
# DÉMARRAGE DU BOT
# -----------------------------------------

@bot.event
async def on_ready():
    await tree.sync()
    print("Bot connecté et commandes synchronisées !")


bot.run("TON_TOKEN_ICI")

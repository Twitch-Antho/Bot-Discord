import discord
from discord.ext import commands
from laws import propose_law, activate_law
from votes import vote, count_votes
from config import TOKEN

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("🧪 Society Bot prêt")
    await bot.tree.sync()

@bot.tree.command(name="loi")
async def loi(interaction: discord.Interaction, titre: str):
    law_id = propose_law(titre)
    await interaction.response.send_message(
        f"📜 Loi proposée #{law_id} : **{titre}**\n"
        "Vote avec `/vote oui` ou `/vote non`"
    )

@bot.tree.command(name="vote")
async def vote_cmd(interaction: discord.Interaction, law_id: int, choix: str):
    vote(law_id, interaction.user.id, choix)
    yes, no = count_votes(law_id)

    if yes >= 3:
        activate_law(law_id)
        await interaction.response.send_message("✅ Loi adoptée !")
    else:
        await interaction.response.send_message(f"🗳️ Votes — Oui: {yes} | Non: {no}")

bot.run(TOKEN)

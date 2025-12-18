import discord
from discord.ext import commands
from config import TOKEN, GUILD_ID, JURY_SIZE
from cases import create_case, close_case
from jury import select_jury

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("⚖️ Justice Bot prêt")
    await bot.tree.sync()

@bot.tree.command(name="juger", description="Ouvrir une affaire")
async def juger(interaction: discord.Interaction, membre: discord.Member, raison: str):
    case_id = create_case(membre.id, raison)

    jury = select_jury(interaction.guild.members, membre.id, JURY_SIZE)
    jury_mentions = ", ".join(j.mention for j in jury)

    await interaction.response.send_message(
        f"⚖️ Affaire #{case_id} ouverte contre **Utilisateur A**\n"
        f"👥 Jury : {jury_mentions}"
    )

bot.run(TOKEN)

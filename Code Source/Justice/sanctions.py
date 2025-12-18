import discord

async def apply_verdict(member: discord.Member, verdict: str):
    if verdict == "AVERTISSEMENT":
        await member.send("⚖️ Avertissement du tribunal communautaire.")
    elif verdict == "MUTE":
        await member.timeout(discord.utils.utcnow(), reason="Justice communautaire")

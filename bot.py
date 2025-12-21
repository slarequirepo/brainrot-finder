import os
import aiohttp
import discord
from discord.ext import tasks, commands
import asyncio
from datetime import datetime
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("1448892285617180756"))
UNIVERSE_ID = 109983668079237
WEBHOOK_URL = "brainrot-finder.zeabur.app"  # Your Zeabur URL

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_servers():
    url = f"https://games.roblox.com/v1/games/{UNIVERSE_ID}/servers/Public"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"limit": 100}) as resp:
            data = await resp.json()
            return [s for s in data.get("data", []) if s["playing"] >= 3]  # Low-pop for easy steal

@tasks.loop(minutes=1)
async def scan():
    channel = bot.get_channel(CHANNEL_ID)
    servers = await fetch_servers()

    good_servers = servers[:5]  # Top 5
    if not good_servers:
        return

    # Send to webhook
    payload = {
        "servers": [
            {
                "id": s['id'],
                "playing": s['playing'],
                "maxPlayers": s['maxPlayers'],
                "ping": s.get('ping', 'N/A')
            }
            for s in good_servers
        ]
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
    except:
        pass

    # Send to Discord
    for srv in good_servers:
        job_id = srv['id']
        join_url = f"roblox://placeId={UNIVERSE_ID}&gameInstanceId={job_id}"
        embed = discord.Embed(title="Brainrot Server", color=0x00ff00)
        embed.add_field(name="Players", value=f"{srv['playing']}/{srv['maxPlayers']}", inline=True)
        embed.add_field(name="Job ID", value=f"`{job_id}`", inline=True)
        embed.add_field(name="Join", value=f"[CLICK]({join_url})", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print("Bot live!")
    scan.start()

bot.run(TOKEN)
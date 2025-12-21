import os
import aiohttp
import discord
from discord.ext import tasks, commands
import asyncio
from datetime import datetime
import requests

# ====== CONFIGURAÇÕES ======
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1448892285617180756"))  # CORRIGIDO: Pega do .env
DISCORD_WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1448892994987233300/FjVTLsLoqfkXJ24Gmg4xc8yPfRhLv8YSxtACBeJCDyDi4pWbNDcTnLSUIAX3MipUi87j")  # Webhook do Discord
ZEABUR_WEBHOOK_URL = os.getenv("ZEABUR_WEBHOOK_URL", "brainrot-finder.zeabur.app")
UNIVERSE_ID = 109983668079237

# ====== BOT SETUP ======
intents = discord.Intents.default()
intents.message_content = True  # IMPORTANTE: Necessário para ler mensagens
bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_servers():
    """Busca servidores do Roblox"""
    url = f"https://games.roblox.com/v1/games/{UNIVERSE_ID}/servers/Public"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"limit": 100}) as resp:
                if resp.status != 200:
                    print(f"❌ Erro ao buscar servidores: {resp.status}")
                    return []
                data = await resp.json()
                # Filtra servidores com 3+ jogadores
                return [s for s in data.get("data", []) if s["playing"] >= 3]
    except Exception as e:
        print(f"❌ Erro no fetch_servers: {e}")
        return []

async def send_to_discord_webhook(servers):
    """Envia notificações para o webhook do Discord"""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL não configurado")
        return
    
    for srv in servers:
        job_id = srv['id']
        join_url = f"roblox://placeId={UNIVERSE_ID}&gameInstanceId={job_id}"
        
        # Embed para webhook do Discord
        embed = {
            "title": "🧠 Brainrot Server Encontrado",
            "color": 65280,  # Verde
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "👥 Players",
                    "value": f"{srv['playing']}/{srv['maxPlayers']}",
                    "inline": True
                },
                {
                    "name": "🆔 Job ID",
                    "value": f"`{job_id}`",
                    "inline": True
                },
                {
                    "name": "🎮 Entrar",
                    "value": f"[CLIQUE AQUI]({join_url})",
                    "inline": False
                }
            ],
            "footer": {"text": "Brainrot Finder"}
        }
        
        if srv.get('ping') and srv['ping'] != 'N/A':
            embed["fields"].append({
                "name": "📶 Ping",
                "value": f"{srv['ping']}ms",
                "inline": True
            })
        
        payload = {"embeds": [embed]}
        
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 204:
                print(f"✅ Discord Webhook: {srv['playing']} players")
            else:
                print(f"⚠️ Discord Webhook status: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro no Discord Webhook: {e}")
        
        await asyncio.sleep(1)  # Evita rate limit

async def send_to_zeabur_webhook(servers):
    """Envia dados para o webhook Zeabur (analytics)"""
    payload = {
        "servers": [
            {
                "id": s['id'],
                "playing": s['playing'],
                "maxPlayers": s['maxPlayers'],
                "ping": s.get('ping', 'N/A')
            }
            for s in servers
        ]
    }
    
    try:
        response = requests.post(ZEABUR_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Zeabur Webhook: {len(servers)} servidores")
    except Exception as e:
        print(f"⚠️ Zeabur Webhook erro: {e}")

@tasks.loop(minutes=1)
async def scan():
    """Escaneia servidores a cada 1 minuto"""
    try:
        print(f"🔍 Escaneando... [{datetime.now().strftime('%H:%M:%S')}]")
        
        servers = await fetch_servers()
        good_servers = servers[:5]  # Top 5
        
        if not good_servers:
            print("   Nenhum servidor encontrado com 3+ jogadores")
            return

        print(f"   📊 Encontrados: {len(good_servers)} servidores")

        # Envia para Discord Webhook
        if DISCORD_WEBHOOK_URL:
            await send_to_discord_webhook(good_servers)
        
        # Envia para Zeabur Webhook (analytics)
        await send_to_zeabur_webhook(good_servers)
        
        # ALTERNATIVA: Postar via Bot no canal
        if CHANNEL_ID and not DISCORD_WEBHOOK_URL:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                for srv in good_servers:
                    job_id = srv['id']
                    join_url = f"roblox://placeId={UNIVERSE_ID}&gameInstanceId={job_id}"
                    
                    embed = discord.Embed(
                        title="🧠 Brainrot Server",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="👥 Players", value=f"{srv['playing']}/{srv['maxPlayers']}", inline=True)
                    embed.add_field(name="🆔 Job ID", value=f"`{job_id}`", inline=True)
                    embed.add_field(name="🎮 Join", value=f"[CLICK]({join_url})", inline=False)
                    embed.set_footer(text="Brainrot Finder")
                    
                    await channel.send(embed=embed)
                    await asyncio.sleep(1)
                    
    except Exception as e:
        print(f"❌ Erro no scan: {e}")

@scan.before_loop
async def before_scan():
    """Aguarda bot estar pronto"""
    await bot.wait_until_ready()
    print("🔍 Scanner iniciado!")

@bot.event
async def on_ready():
    """Bot online"""
    print("=" * 60)
    print(f"✅ Bot: {bot.user.name} (ID: {bot.user.id})")
    print(f"📡 Servidores: {len(bot.guilds)}")
    print(f"🎮 Universe ID: {UNIVERSE_ID}")
    print(f"💬 Discord Webhook: {'✅' if DISCORD_WEBHOOK_URL else '❌'}")
    print(f"🌐 Zeabur Webhook: {ZEABUR_WEBHOOK_URL}")
    if CHANNEL_ID:
        print(f"📢 Canal ID: {CHANNEL_ID}")
    print("=" * 60)
    
    if not scan.is_running():
        scan.start()

# ====== COMANDOS ======
@bot.command(name='status')
async def status(ctx):
    """Mostra status do bot"""
    embed = discord.Embed(title="📊 Status", color=0x00ff00)
    embed.add_field(name="🤖 Bot", value=bot.user.name, inline=True)
    embed.add_field(name="🔍 Scanner", value="✅ Ativo" if scan.is_running() else "❌ Inativo", inline=True)
    embed.add_field(name="💬 Webhook", value="✅" if DISCORD_WEBHOOK_URL else "❌", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='scan')
@commands.has_permissions(administrator=True)
async def manual_scan(ctx):
    """Scan manual (admin)"""
    await ctx.send("🔍 Escaneando...")
    await scan()
    await ctx.send("✅ Concluído!")

@bot.command(name='test')
@commands.has_permissions(administrator=True)
async def test_webhook(ctx):
    """Testa webhook"""
    if not DISCORD_WEBHOOK_URL:
        await ctx.send("❌ Webhook não configurado!")
        return
    
    test = [{"id": "test", "playing": 5, "maxPlayers": 10, "ping": 50}]
    await send_to_discord_webhook(test)
    await ctx.send("✅ Teste enviado!")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sem permissão!")
    elif isinstance(error, commands.CommandNotFound):
        pass

# ====== INICIAR ======
if __name__ == '__main__':
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Erro: {e}")
import os
import aiohttp
import discord
from discord.ext import tasks, commands
import asyncio
from datetime import datetime
import requests

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 1448892285617180756))  # Opcional agora
DISCORD_WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1448892994987233300/FjVTLsLoqfkXJ24Gmg4xc8yPfRhLv8YSxtACBeJCDyDi4pWbNDcTnLSUIAX3MipUi87j")  # Webhook do Discord
ZEABUR_WEBHOOK_URL = "brainrot-finder.zeabur.app"  # Seu servidor
UNIVERSE_ID = 109983668079237

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def fetch_servers():
    """Busca servidores públicos do jogo Roblox"""
    url = f"https://games.roblox.com/v1/games/{UNIVERSE_ID}/servers/Public"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params={"limit": 100}) as resp:
            if resp.status != 200:
                print(f"Erro ao buscar servidores: {resp.status}")
                return []
            data = await resp.json()
            # Filtra servidores com pelo menos 3 jogadores
            return [s for s in data.get("data", []) if s["playing"] >= 3]

async def send_to_discord_webhook(servers):
    """Envia notificações para o webhook do Discord"""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL não configurado")
        return
    
    for srv in servers:
        job_id = srv['id']
        join_url = f"roblox://placeId={UNIVERSE_ID}&gameInstanceId={job_id}"
        
        # Cria o embed para o webhook
        embed = {
            "title": "🧠 Brainrot Server Encontrado",
            "color": 65280,  # Verde em decimal (0x00ff00)
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
            "footer": {
                "text": "Brainrot Finder"
            }
        }
        
        # Adiciona ping se disponível
        if srv.get('ping') and srv['ping'] != 'N/A':
            embed["fields"].append({
                "name": "📶 Ping",
                "value": f"{srv['ping']}ms",
                "inline": True
            })
        
        # Payload para o webhook do Discord
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
            if response.status_code == 204:
                print(f"✅ Enviado para Discord Webhook: {srv['playing']} players")
            else:
                print(f"⚠️ Webhook Discord respondeu: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro ao enviar para Discord Webhook: {e}")
        
        await asyncio.sleep(1)  # Evita rate limit

async def send_to_zeabur_webhook(servers):
    """Envia dados para o webhook do Zeabur (para logging/analytics)"""
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
            print(f"✅ Dados enviados para Zeabur: {len(servers)} servidores")
        else:
            print(f"⚠️ Zeabur respondeu: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao enviar para Zeabur: {e}")

@tasks.loop(minutes=1)
async def scan():
    """Escaneia servidores a cada minuto"""
    try:
        servers = await fetch_servers()
        
        # Pega os top 5 servidores
        good_servers = servers[:5]
        if not good_servers:
            print("Nenhum servidor encontrado com 3+ jogadores")
            return

        print(f"🔍 Encontrados {len(good_servers)} servidores")

        # Envia para Discord Webhook (principal)
        await send_to_discord_webhook(good_servers)
        
        # Envia para Zeabur Webhook (opcional - para analytics)
        await send_to_zeabur_webhook(good_servers)
        
        # ============================================
        # ALTERNATIVA: Postar via Bot (se preferir)
        # ============================================
        # Se você quiser usar o bot ao invés do webhook, descomente:
        """
        if CHANNEL_ID:
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                for srv in good_servers:
                    job_id = srv['id']
                    join_url = f"roblox://placeId={UNIVERSE_ID}&gameInstanceId={job_id}"
                    
                    embed = discord.Embed(
                        title="🧠 Brainrot Server Encontrado",
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="👥 Players", value=f"{srv['playing']}/{srv['maxPlayers']}", inline=True)
                    embed.add_field(name="🆔 Job ID", value=f"`{job_id}`", inline=True)
                    embed.add_field(name="🎮 Entrar", value=f"[CLIQUE AQUI]({join_url})", inline=False)
                    
                    if srv.get('ping') and srv['ping'] != 'N/A':
                        embed.add_field(name="📶 Ping", value=f"{srv['ping']}ms", inline=True)
                    
                    embed.set_footer(text="Brainrot Finder")
                    
                    await channel.send(embed=embed)
                    await asyncio.sleep(1)
        """
                
    except Exception as e:
        print(f"❌ Erro no scan: {e}")

@scan.before_loop
async def before_scan():
    """Aguarda o bot estar pronto antes de iniciar o scan"""
    await bot.wait_until_ready()
    print("🔍 Scanner iniciado!")

@bot.event
async def on_ready():
    """Evento quando o bot está online"""
    print("=" * 50)
    print(f"✅ Bot online como {bot.user.name} ({bot.user.id})")
    print(f"🎮 Universe ID: {UNIVERSE_ID}")
    print(f"🌐 Zeabur Webhook: {ZEABUR_WEBHOOK_URL}")
    print(f"💬 Discord Webhook: {'✅ Configurado' if DISCORD_WEBHOOK_URL else '❌ Não configurado'}")
    if CHANNEL_ID:
        print(f"📡 Canal (alternativo): {CHANNEL_ID}")
    print("=" * 50)
    
    if not scan.is_running():
        scan.start()

@bot.command(name='status')
async def status(ctx):
    """Mostra o status do bot"""
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="🤖 Bot", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="🔍 Scanner", value="✅ Ativo" if scan.is_running() else "❌ Inativo", inline=True)
    embed.add_field(name="🎮 Universe ID", value=UNIVERSE_ID, inline=False)
    embed.add_field(name="💬 Discord Webhook", value="✅ Ativo" if DISCORD_WEBHOOK_URL else "❌ Não configurado", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='scan')
@commands.has_permissions(administrator=True)
async def manual_scan(ctx):
    """Força um scan manual (apenas admin)"""
    await ctx.send("🔍 Iniciando scan manual...")
    await scan()
    await ctx.send("✅ Scan concluído!")

@bot.command(name='test_webhook')
@commands.has_permissions(administrator=True)
async def test_webhook(ctx):
    """Testa o webhook do Discord"""
    if not DISCORD_WEBHOOK_URL:
        await ctx.send("❌ DISCORD_WEBHOOK_URL não configurado!")
        return
    
    await ctx.send("🧪 Testando webhook...")
    
    test_server = {
        "id": "test-12345",
        "playing": 5,
        "maxPlayers": 10,
        "ping": 50
    }
    
    await send_to_discord_webhook([test_server])
    await ctx.send("✅ Teste enviado! Verifique o canal do webhook.")

@bot.event
async def on_command_error(ctx, error):
    """Tratamento de erros"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando!")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Erro: {error}")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ ERRO: DISCORD_TOKEN não encontrado!")
        print("Configure a variável de ambiente DISCORD_TOKEN")
        exit(1)
    
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ AVISO: DISCORD_WEBHOOK_URL não configurado!")
        print("As notificações não serão enviadas para o Discord")
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
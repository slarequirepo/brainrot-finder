from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn
import os

app = FastAPI(title="Brainrot Finder Webhook")

# Armazena últimos servidores
LATEST_SERVERS = []

@app.get("/")
async def home():
    """Página inicial - verifica se está online"""
    return {
        "status": "online",
        "service": "Brainrot Finder Webhook",
        "timestamp": datetime.now().isoformat(),
        "servers_count": len(LATEST_SERVERS),
        "endpoints": {
            "post_data": "/brainrot-alert",
            "get_data": "/get-servers",
            "health": "/health"
        }
    }

@app.post("/brainrot-alert")
async def receive_alert(request: Request):
    """Recebe dados dos servidores do bot"""
    global LATEST_SERVERS
    
    try:
        data = await request.json()
        
        if not data or 'servers' not in data:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid payload - 'servers' key required"}
            )
        
        LATEST_SERVERS = data.get("servers", [])[:5]
        
        # Log
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Recebidos {len(LATEST_SERVERS)} servidores:")
        for srv in LATEST_SERVERS:
            print(f"  → ID: {srv.get('id')} | Players: {srv.get('playing')}/{srv.get('maxPlayers')}")
        
        return {
            "ok": True,
            "received": len(LATEST_SERVERS),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/get-servers")
async def get_servers():
    """Retorna últimos servidores encontrados"""
    return {
        "servers": LATEST_SERVERS,
        "count": len(LATEST_SERVERS),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "uptime": "ok"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
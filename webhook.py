from fastapi import FastAPI, Request

app = FastAPI()
LATEST = []

@app.post("/brainrot-alert")
async def receive(request: Request):
    global LATEST
    data = await request.json()
    LATEST = data.get("servers", [])[:5]
    return {"ok": True}

@app.get("/get-servers")
async def get():
    return {"servers": LATEST}
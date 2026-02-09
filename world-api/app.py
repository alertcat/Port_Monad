"""Port Monad World API - FastAPI main entry"""
import os
from pathlib import Path

# Load .env from project root BEFORE anything else
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.openapi.utils import get_openapi

from engine.state import get_world_engine

# API metadata
API_TITLE = "Port Monad World API"
API_VERSION = "0.2.0"
API_DESCRIPTION = """
# Port Monad World API

Token-gated persistent world for AI agents on Monad blockchain.

## Authentication

### Option 1: Moltbook Identity (Recommended)
Include your Moltbook identity token in the `X-Moltbook-Identity` header.

Get auth instructions: `GET /moltbook/auth-info`

### Option 2: Direct Wallet
Include your wallet address in the `X-Wallet` header.

**Note**: Both methods require an active entry on the WorldGate contract.

## Contract Information
- **Address**: `0x2894D907B3f4c37Cc521352204aE2FfeD78f3463`
- **Chain**: Monad Mainnet (143)
- **Entry Fee**: 1 MON
- **Entry Duration**: 7 days

## OpenClaw Skill
Read the skill file at `/skill.md` for AI agent integration.
"""

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    """Serve the web dashboard"""
    dashboard_file = static_dir / "index.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file))
    return {"error": "Dashboard not found"}

@app.get("/game", include_in_schema=False)
async def game_view():
    """Serve the Smallville-style game world view"""
    game_file = static_dir / "game.html"
    if game_file.exists():
        return FileResponse(str(game_file))
    return {"error": "Game view not found"}

@app.get("/game3d", include_in_schema=False)
async def game3d_view():
    """Serve the Three.js 3D world view"""
    game_file = static_dir / "game3d.html"
    if game_file.exists():
        return FileResponse(str(game_file))
    return {"error": "3D game view not found"}

@app.get("/pyth/price")
async def pyth_price():
    """Get real-time MON/USD price from Pyth oracle (affects market prices)"""
    from engine.pyth_oracle import get_pyth_feed
    feed = get_pyth_feed()
    price = feed.get_mon_usd_price()
    baseline = feed.baseline_price
    change_pct = 0.0
    if baseline and price:
        change_pct = ((price - baseline) / baseline) * 100
    return {
        "mon_usd": price,
        "baseline": baseline,
        "change_pct": round(change_pct, 4),
        "source": "Pyth Network (MON/USD)",
        "cache_ttl_s": 30
    }

@app.get("/demo", include_in_schema=False)
async def demo_page():
    """Serve the demo control panel for judges"""
    demo_file = static_dir / "demo.html"
    if demo_file.exists():
        return FileResponse(str(demo_file))
    return {"error": "Demo page not found"}

# ---------------------------------------------------------------------------
# Demo runner: judges can trigger full game from browser
# ---------------------------------------------------------------------------
import subprocess
import sys
import threading
import time as _time

_demo_state = {
    "running": False,
    "log": "",
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "pid": None,
}
_demo_lock = threading.Lock()

def _run_demo_background(rounds, cycles, cycle_wait):
    """Run run_full_game.py in background, capture output."""
    global _demo_state
    script = str(Path(__file__).parent.parent / "scripts" / "run_full_game.py")
    cmd = [
        sys.executable, script,
        "--rounds", str(rounds),
        "--cycles", str(cycles),
        "--cycle-wait", str(cycle_wait),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(Path(__file__).parent.parent),
        )
        with _demo_lock:
            _demo_state["pid"] = proc.pid
        for line in proc.stdout:
            with _demo_lock:
                _demo_state["log"] += line
        proc.wait()
        with _demo_lock:
            _demo_state["exit_code"] = proc.returncode
            _demo_state["finished_at"] = _time.time()
            _demo_state["running"] = False
    except Exception as e:
        with _demo_lock:
            _demo_state["log"] += f"\n\nERROR: {e}\n"
            _demo_state["running"] = False
            _demo_state["exit_code"] = -1
            _demo_state["finished_at"] = _time.time()

@app.post("/demo/start")
async def demo_start(rounds: int = 5, cycles: int = 1, cycle_wait: int = 30):
    """Start a full game demo (judges can trigger remotely)"""
    with _demo_lock:
        if _demo_state["running"]:
            return {"error": "Demo already running", "started_at": _demo_state["started_at"]}
        _demo_state["running"] = True
        _demo_state["log"] = ""
        _demo_state["started_at"] = _time.time()
        _demo_state["finished_at"] = None
        _demo_state["exit_code"] = None
        _demo_state["pid"] = None

    t = threading.Thread(target=_run_demo_background, args=(rounds, cycles, cycle_wait), daemon=True)
    t.start()
    return {"status": "started", "rounds": rounds, "cycles": cycles, "cycle_wait": cycle_wait}

@app.get("/demo/status")
async def demo_status():
    """Get demo run status and log"""
    with _demo_lock:
        elapsed = None
        if _demo_state["started_at"]:
            end = _demo_state["finished_at"] or _time.time()
            elapsed = round(end - _demo_state["started_at"], 1)
        return {
            "running": _demo_state["running"],
            "exit_code": _demo_state["exit_code"],
            "elapsed_s": elapsed,
            "log_lines": _demo_state["log"].count("\n"),
        }

@app.get("/demo/log")
async def demo_log(offset: int = 0):
    """Get demo log output (use offset to get incremental updates)"""
    with _demo_lock:
        log = _demo_state["log"]
        return {
            "running": _demo_state["running"],
            "exit_code": _demo_state["exit_code"],
            "total_length": len(log),
            "offset": offset,
            "content": log[offset:],
        }

@app.post("/demo/stop")
async def demo_stop():
    """Stop a running demo"""
    with _demo_lock:
        if not _demo_state["running"] or not _demo_state["pid"]:
            return {"error": "No demo running"}
        pid = _demo_state["pid"]
    try:
        import signal
        os.kill(pid, signal.SIGTERM)
        return {"status": "stopped", "pid": pid}
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "world": "Port Monad", "version": API_VERSION}

@app.get("/")
async def root():
    """World basic info"""
    world = get_world_engine()
    return {
        "name": "Port Monad",
        "description": "A persistent port city for AI agents",
        "version": API_VERSION,
        "entry_fee": "1 MON",
        "tick": world.state.tick,
        "contract": os.getenv("WORLDGATE_ADDRESS", "0x2894D907B3f4c37Cc521352204aE2FfeD78f3463"),
        "chain_id": 143,
        "docs": "/docs",
        "dashboard": "/dashboard",
        "game_2d": "/game",
        "game_3d": "/game3d",
        "pyth_oracle": "/pyth/price",
        "skill": "/skill.md",
        "moltbook_auth": "/moltbook/auth-info"
    }

@app.get("/world/meta")
async def world_meta():
    """World metadata: rules, fees, available actions"""
    return {
        "entry_fee": "1 MON",
        "entry_duration_days": 7,
        "regions": ["dock", "market", "mine", "forest"],
        "resources": ["iron", "wood", "fish"],
        "actions": {
            "move": {"ap_cost": 5, "description": "Move to another region"},
            "harvest": {"ap_cost": 10, "description": "Collect resources"},
            "rest": {"ap_cost": 0, "description": "Rest to recover AP"},
            "place_order": {"ap_cost": 3, "description": "Place market order"},
            "raid": {"ap_cost": 25, "description": "Combat: Attack agent in same region to steal credits"},
            "negotiate": {"ap_cost": 15, "description": "Politics: Propose trade with agent in same region"}
        },
        "ap_recovery_per_tick": 5,
        "contract": {
            "address": os.getenv("WORLDGATE_ADDRESS", "0x2894D907B3f4c37Cc521352204aE2FfeD78f3463"),
            "chain_id": 143,
            "rpc": "https://rpc.monad.xyz"
        },
        "dashboard": "/dashboard",
        "game_2d": "/game",
        "game_3d": "/game3d",
        "pyth_oracle": "/pyth/price"
    }

@app.get("/world/state")
async def world_state():
    """Public world state including tick, events, and market prices"""
    world = get_world_engine()
    return world.get_public_state()

@app.get("/agent/{wallet}/state")
async def agent_state(wallet: str):
    """Get agent state by wallet address"""
    world = get_world_engine()
    agent = world.get_agent(wallet)
    if not agent:
        return {"error": "Agent not found", "wallet": wallet}
    return agent.to_dict()

@app.get("/skill.md", include_in_schema=False)
async def skill_file():
    """Serve OpenClaw SKILL.md for AI agent integration"""
    from fastapi.responses import PlainTextResponse
    skill_path = os.path.join(os.path.dirname(__file__), "..", "openclaw", "SKILL.md")
    try:
        with open(skill_path, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read(), media_type="text/markdown")
    except FileNotFoundError:
        return PlainTextResponse("# Port Monad Skill\n\nSkill file not found.", media_type="text/markdown")

# Import routes
from routes.action import router as action_router
app.include_router(action_router)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "MoltbookIdentity": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Moltbook-Identity",
            "description": "Moltbook identity token for bot authentication"
        },
        "WalletAddress": {
            "type": "apiKey",
            "in": "header", 
            "name": "X-Wallet",
            "description": "Ethereum wallet address"
        }
    }
    
    # Add server info
    openapi_schema["servers"] = [
        {"url": "https://eating-sector-rendering-creations.trycloudflare.com", "description": "Production server (HTTPS)"},
        {"url": "http://43.156.62.248", "description": "Production server (direct IP)"},
        {"url": "http://localhost:8000", "description": "Local development"}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    import socket
    import sys
    
    port = 8000
    
    # Check if port is already in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    
    if result == 0:
        print(f"\n❌ ERROR: Port {port} is already in use!")
        print(f"   Kill the old process first:")
        print(f"   Windows:  netstat -ano | findstr :{port}")
        print(f"             taskkill /F /PID <PID>")
        print(f"   Linux:    kill $(lsof -t -i:{port})")
        sys.exit(1)
    
    print(f"\n🚀 Starting Port Monad World API on port {port}")
    print(f"   DEBUG_MODE: {os.getenv('DEBUG_MODE', 'false')}")
    print(f"   MOLTBOOK_DRY_RUN: {os.getenv('MOLTBOOK_DRY_RUN', 'false')}")
    print(f"   Dashboard: http://localhost:{port}/dashboard")
    print(f"   API Docs:  http://localhost:{port}/docs\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)

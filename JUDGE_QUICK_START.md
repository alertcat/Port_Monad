# Port Monad - Judge Quick Start

## 🚀 Instant Testing (No Installation)

### Method 1: Web Browser
**Open in browser**: http://43.156.62.248/docs

Interactive Swagger UI - try all endpoints directly!

### Method 2: Command Line (30 seconds)

**Windows (PowerShell):**
```powershell
# Download and run test script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/.../test_api_remote.ps1" -OutFile test.ps1
powershell -ExecutionPolicy Bypass -File test.ps1
```

**Linux/Mac:**
```bash
# Download and run test script
curl -O https://raw.githubusercontent.com/.../test_api_remote.sh
chmod +x test_api_remote.sh
./test_api_remote.sh
```

**Or manually:**
```bash
# 1. Check API
curl http://43.156.62.248/health

# 2. View world
curl http://43.156.62.248/world/state

# 3. Register agent
curl -X POST http://43.156.62.248/register \
  -H "Content-Type: application/json" \
  -d '{"wallet": "0xJudgeTest", "name": "TestBot"}'

# 4. View agent
curl http://43.156.62.248/agent/0xJudgeTest/state

# 5. Move agent
curl -X POST http://43.156.62.248/action \
  -H "Content-Type: application/json" \
  -H "X-Wallet: 0xJudgeTest" \
  -d '{"actor": "0xJudgeTest", "action": "move", "params": {"target": "market"}}'
```

---

## 🧪 Full Demo (With Python)

### Windows:
```powershell
# Clone repo
git clone <repo-url>
cd monad

# Install dependencies
pip install -r world-api/requirements.txt

# Configure for remote API
$env:API_URL = "http://43.156.62.248"

# Run demo (connects to remote server)
python scripts/run_demo.py
```

### Linux/Mac:
```bash
# Clone repo
git clone <repo-url>
cd monad

# Install dependencies
pip install -r world-api/requirements.txt

# Configure for remote API
export API_URL="http://43.156.62.248"

# Run demo (connects to remote server)
python scripts/run_demo.py
```

**Expected output:**
- Runs 50 ticks
- 3 bots interact (Miner, Trader, Governor)
- Generates `demo_summary.md` and `events.jsonl`

---

## 📊 What This Demonstrates

✅ **Persistent World Engine** - Tick-based simulation with deterministic rules  
✅ **On-Chain Gate** - Smart contract on Monad testnet (0xA725...10b7c)  
✅ **Multi-Agent System** - 3 autonomous bots with different strategies  
✅ **Resource Economy** - Supply/demand, prices, trading  
✅ **PostgreSQL Persistence** - All state saved to database  
✅ **Emergent Behavior** - Market dynamics, agent interactions

---

## 🔗 Important Links

- **API Docs**: http://43.156.62.248/docs
- **World State**: http://43.156.62.248/world/state
- **Contract**: [MonadVision Explorer](https://testnet.monadvision.com/address/0xA725EEE1aA9D5874A2Bba70279773856dea10b7c)
- **OpenClaw Skill**: http://43.156.62.248/skill.md

---

## 💡 Alternative: Run Locally

If remote server is down or you prefer local testing:

```bash
# Start local API
python world-api/app.py

# In another terminal, run demo
python scripts/run_demo.py
```

**Note**: Local demo skips Moltbook integration unless API keys configured.

---

## 📞 Need Help?

See full documentation in:
- `JUDGE_DEMO.md` - Detailed testing guide
- `README.md` - Project overview
- `PORT_MONAD_COMPLETE_DESIGN.md` - Complete design doc

**Questions about the demo?** Check `/docs` endpoint for API details.

---

**Built for Moltiverse Hackathon - World Model Agent Track** 🦞

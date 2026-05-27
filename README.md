# 🌿 EcoBot – Product Eco-Assessment Telegram Bot

Scans any product (via photo or barcode) and reports:
- 🧬 Health safety (microplastics, chemicals, allergens, carcinogens)
- 🌍 Ecological impact (Eco-Score, palm oil, packaging, carbon footprint)
- 🏅 Certifications (organic, vegan, cruelty-free)
- 🚨 Greenwashing flags

---

## 📁 Project Structure

```
ecobot/
├── main.py          # FastAPI app + bot lifecycle
├── bot.py           # Telethon bot handlers
├── gpt_client.py    # OpenAI API calls
├── barcode.py       # Barcode detection + Open Food Facts
├── formatter.py     # Telegram message formatter
├── prompts.py       # All GPT prompts
├── models.py        # SQLAlchemy DB models
├── database.py      # DB engine + session
├── env.py           # Env var loader
├── cronjob.py       # Keep-alive pinger
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── render.yaml
```

---

## ⚙️ Setup (Local, VSCode)

### 1. Clone & install

```bash
cd ecobot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get your credentials

| Credential | Where to get it |
|---|---|
| `API_ID` + `API_HASH` | https://my.telegram.org → "API development tools" |
| `BOT_TOKEN` | @BotFather on Telegram → /newbot |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

### 3. Configure .env

```bash
cp .env.example .env
# Fill in all values in .env
```

For **local** PostgreSQL (no SSL needed):
```
DATABASE_URL=postgresql://ecobot:ecobot@localhost:5432/ecobot
```

### 4. Start PostgreSQL (Docker)

```bash
docker compose up db -d
```

Or install PostgreSQL locally and create the DB:
```bash
createdb ecobot
```

### 5. Run the bot

```bash
uvicorn main:app --reload
```

The bot starts automatically. Open Telegram and message your bot.

---

## 🐳 Run Everything with Docker

```bash
docker compose up --build
```

---

## 🚀 Deploy to Render.com

1. Push code to GitHub
2. Go to https://render.com → New → Blueprint
3. Select your repo — Render reads `render.yaml` automatically
4. Set environment variables in the Render dashboard:
   - `API_ID`, `API_HASH`, `BOT_TOKEN`, `OPENAI_API_KEY`
   - `DATABASE_URL` is auto-filled from the managed Postgres

### Keep-alive (free tier)

Free Render instances sleep after 15 min. Use cron-job.org (free) to ping your URL every 10 min:
- URL: `https://your-app.onrender.com/`
- Schedule: `*/10 * * * *`

Or run locally: `python cronjob.py`

---

## 📱 How to Use the Bot

| Action | What to do |
|---|---|
| Scan a product | Send any product photo |
| Barcode lookup | Type the barcode number (e.g. `5000112548167`) |
| Help | `/help` |

---

## 🗄️ Database Tables

- **users** – Telegram users
- **product_scans** – Every scan with full eco analysis

View stats: `GET /stats`  
User history: `GET /scans/{telegram_id}`

---

## 🔧 Troubleshooting

**pyzbar not working on Windows?**
Install the Visual C++ Redistributable and `zbar` DLLs:
```
pip install pyzbar[scripts]
python -m pyzbar  # installs zbar DLLs automatically
```

**"Session already in use" error?**
Delete `ecobot_session.session` and restart.

**OpenAI rate limits?**
The bot uses `gpt-4o` for images and `gpt-4o-mini` for text — mini is much cheaper.

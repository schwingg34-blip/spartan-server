# Spartan SMC — Server Setup Guide

## What this is
A Python FastAPI server that:
- Receives TradingView webhook alerts at `/webhook`
- Broadcasts signals to your dashboard in real time via WebSocket
- Serves the dashboard at `/` (your Railway URL)

---

## Step 1 — Push to GitHub

1. Go to github.com → New Repository → name it `spartan-server` → Create
2. Open Terminal (Mac) or Command Prompt (Windows) in this folder
3. Run these commands one by one:

```bash
git init
git add .
git commit -m "initial spartan server"
git remote add origin https://github.com/YOUR_USERNAME/spartan-server.git
git push -u origin main
```

---

## Step 2 — Deploy on Railway

1. Go to railway.app → Sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `spartan-server` repository
4. Railway auto-detects Python and deploys — takes ~2 minutes
5. Click your project → **Settings** → **Networking** → **Generate Domain**
6. Your URL will look like: `https://spartan-server-production-xxxx.up.railway.app`

---

## Step 3 — Set Webhook in TradingView

1. Open TradingView → add Spartan SMC indicator to your chart
2. Click the alert (bell) icon → Create Alert
3. Condition: **Spartan SMC** → **Any alert() function call**
4. Notifications tab → check **Webhook URL**
5. Paste your Railway URL + `/webhook`:
   ```
   https://spartan-server-production-xxxx.up.railway.app/webhook
   ```
6. Message field: leave completely blank
7. Click Create

---

## Step 4 — Open Dashboard

Go to your Railway URL in any browser:
```
https://spartan-server-production-xxxx.up.railway.app
```

The dashboard connects automatically via WebSocket. When TradingView fires an alert, the signal appears on your dashboard within ~1 second.

---

## Endpoints

| Endpoint       | Method | Description                        |
|---------------|--------|------------------------------------|
| `/`           | GET    | Dashboard UI                       |
| `/webhook`    | POST   | Receives TradingView alerts        |
| `/ws`         | WS     | WebSocket for real-time dashboard  |
| `/signals`    | GET    | JSON list of recent signals        |
| `/health`     | GET    | Server status check                |

---

## Test the webhook manually

Once deployed, you can test without TradingView:

```bash
curl -X POST https://YOUR-RAILWAY-URL/webhook \
  -H "Content-Type: application/json" \
  -d '{"contract":"MNQ","asset":"Futures","direction":"LONG","strength":"STRONG","score":88,"entry":19842.50,"sl":19821.25,"tp1":19863.75,"tp2":19897.25,"doubt":"false","htf":"bull","volSpike":"true","bos":"true","choch":"false","bullFVG":"true","bearFVG":"false"}'
```

You should see the signal appear on the dashboard immediately.

---

## Railway Free Tier Notes
- 500 hours/month free — enough for active trading hours
- Sleeps after inactivity — wakes up within ~5s on first request
- To keep it always awake, upgrade to Railway Hobby ($5/month)

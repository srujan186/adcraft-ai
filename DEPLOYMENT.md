# AdCraft AI — Deployment Guide

---

## 🚀 Option A — Vercel (Frontend Demo)

Deploy the **Next.js frontend** to Vercel for free. The backend still needs to be running somewhere accessible (e.g. your local machine via ngrok, or Oracle Cloud).

### Step 1 — Push frontend to GitHub

```bash
# From the project root
git add frontend/
git commit -m "feat: add Next.js frontend"
git push
```

### Step 2 — Import on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import your GitHub repo (`adcraft-ai`)
3. Set **Root Directory** → `frontend`
4. Vercel auto-detects Next.js — no build changes needed
5. Click **Deploy**

### Step 3 — Set the Backend URL

After deploy, go to **Project Settings → Environment Variables** and add:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | `http://<your-backend-ip-or-ngrok-url>` |

Then **Redeploy** once from the Vercel dashboard.

> **Note:** If you're running the backend locally and want Vercel to reach it, use [ngrok](https://ngrok.com):
> ```bash
> ngrok http 8000
> # Use the https://xxxx.ngrok-free.app URL as NEXT_PUBLIC_API_URL
> ```
> Also add the ngrok URL to `ALLOWED_ORIGINS` in `backend/.env`.

### Step 4 — Done

Your frontend is live at `https://adcraft-ai-xxxx.vercel.app` 🎉

---

## ☁️ Option B — Oracle Cloud Free Tier (Full Stack)

# AdCraft AI — Oracle Cloud Free Tier Deployment


## What you get (Always Free — no charges)
| Resource | Spec |
|----------|------|
| VM | Ampere A1 Flex — **4 OCPUs, 24 GB RAM** |
| Storage | 200 GB block volume |
| Bandwidth | 10 TB/month outbound |
| OS | Ubuntu 22.04 LTS |

---

## Step 1 — Create the Oracle Cloud VM

1. Sign in at [cloud.oracle.com](https://cloud.oracle.com)
2. Go to **Compute → Instances → Create Instance**
3. Settings:
   - **Image**: Canonical Ubuntu 22.04
   - **Shape**: `VM.Standard.A1.Flex` → 4 OCPUs, 24 GB RAM
   - **SSH key**: upload your public key (`~/.ssh/id_rsa.pub`)
4. Click **Create**. Note the **Public IP** from the instance details.

---

## Step 2 — Open Firewall Ports

In Oracle Cloud Console → **Virtual Cloud Network → Security Lists → Default Security List**:

Add **Ingress** rules:
| Protocol | Port | Description |
|----------|------|-------------|
| TCP | 22 | SSH |
| TCP | 80 | HTTP (Nginx) |
| TCP | 8000 | FastAPI (optional, for direct API access) |

Also run on the VM (Ubuntu firewall):
```bash
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 8000
sudo ufw enable
```

---

## Step 3 — Install Docker on the VM

SSH in first:
```bash
ssh ubuntu@<YOUR_VM_PUBLIC_IP>
```

Then install Docker:
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Allow running docker without sudo
sudo usermod -aG docker ubuntu
newgrp docker
```

Verify:
```bash
docker --version && docker compose version
```

---

## Step 4 — Deploy AdCraft AI

```bash
# 1. Clone your repo
git clone https://github.com/YOUR_GITHUB_USERNAME/adcraft-ai.git
cd adcraft-ai

# 2. Set up environment file
cp backend/.env.example backend/.env
nano backend/.env   # Fill in your API keys + set ALLOWED_ORIGINS
```

In `backend/.env` set:
```env
GROQ_API_KEY=gsk_...
PEXELS_API_KEY=...
ALLOWED_ORIGINS=http://<YOUR_VM_PUBLIC_IP>
```

In `docker-compose.yml`, update the frontend `NEXT_PUBLIC_API_URL` arg:
```yaml
args:
  NEXT_PUBLIC_API_URL: http://<YOUR_VM_PUBLIC_IP>/api
```

Then build and launch:
```bash
# 3. Build and start (first build takes ~10–15 min due to Playwright)
docker compose up -d --build

# 4. Check all services are up
docker compose ps
docker compose logs -f   # Ctrl+C to exit
```

---

## Step 5 — Access Your App

Open in browser:
```
http://<YOUR_VM_PUBLIC_IP>
```

API docs:
```
http://<YOUR_VM_PUBLIC_IP>/docs
```

---

## Updating After Code Changes

```bash
cd adcraft-ai
git pull
docker compose up -d --build
```

---

## Useful Commands

```bash
# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Restart a single service
docker compose restart backend

# Stop everything
docker compose down

# View generated videos
ls backend/output/
```

---

> **Tip:** Generated `.mp4` files are stored in `backend/output/` which is mounted as a Docker volume, so they survive container restarts and rebuilds.

# CivicResolve AI - Vercel Cloud Deployment Guide

## 1. Overview
CivicResolve AI is fully configured for **serverless cloud deployment on Vercel**.
- **Backend**: FastAPI multi-agent API deployed as Vercel Serverless Functions (`api/index.py` using `@vercel/python`).
- **Frontend**: Responsive, multilingual Dubai smart-city web interface (`public/index.html`, `public/style.css`, `public/app.js`) with 6-language switcher and native Arabic/Urdu RTL support.
- **Serverless Optimization**: SQLite runs in `/tmp/civicresolve.db` with temporary file isolation.
- **External Webhooks**: Pre-wired to AskDubai n8n cloud triggers:
  - File New Complaint: `https://askdubai.app.n8n.cloud/form/civicresolve`
  - Check / Update Case: `https://askdubai.app.n8n.cloud/form/civicresolve-update`

---

## 2. Deployment Method A: Direct GitHub Integration (Recommended)

1. Push your code to your GitHub repository (`github.com/<username>/askdubai`).
2. Log into [Vercel](https://vercel.com/) and click **"Add New..."** > **"Project"**.
3. Import your **`askdubai`** repository.
4. Keep the root directory as `./` (or select `civicresolve-ai` if deploying the subfolder alone).
5. Vercel automatically reads [`vercel.json`](../vercel.json) and configures the Python serverless runtime and static assets.
6. Click **"Deploy"**.
7. Your app will be live at `https://askdubai.vercel.app` (or your assigned Vercel URL)!

---

## 3. Deployment Method B: Using Vercel CLI

From your local machine terminal:
```bash
# 1. Install or run Vercel CLI via npx (no global install needed)
npx vercel

# 2. Follow the interactive prompts:
# ? Set up and deploy "~/github/askdubai"? [Y/n] Y
# ? Which scope do you want to deploy to? [Your Team/Account]
# ? Link to existing project? [y/N] N
# ? What's your project's name? civicresolve-ai
# ? In which directory is your code located? ./

# 3. Deploy to production
npx vercel --prod
```

---

## 4. Environment Variables on Vercel Dashboard

Under **Project Settings > Environment Variables**, you can configure:

| Key | Recommended Value | Description |
| :--- | :--- | :--- |
| `CIVICRESOLVE_ENV` | `production` | Production mode switch |
| `SECRET_KEY` | *(generate a random 32-character key)* | JWT signing key |
| `DATABASE_URL` | `sqlite:////tmp/civicresolve.db` | Serverless database path |
| `N8N_NEW_COMPLAINT_URL` | `https://askdubai.app.n8n.cloud/form/civicresolve` | Authorized new complaint form |
| `N8N_UPDATE_CASE_URL` | `https://askdubai.app.n8n.cloud/form/civicresolve-update` | Authorized case update form |

---

## 5. Live Endpoints on Vercel
Once deployed:
- **Interactive Web App**: `https://<your-project>.vercel.app/`
- **FastAPI OpenAPI Docs**: `https://<your-project>.vercel.app/docs`
- **Health Check API**: `https://<your-project>.vercel.app/api/v1/health`
- **Chat & Multi-Agent API**: `https://<your-project>.vercel.app/api/v1/chat`
- **Complaints API**: `https://<your-project>.vercel.app/api/v1/complaints`

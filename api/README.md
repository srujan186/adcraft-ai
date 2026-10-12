---
title: AdCraft API
emoji: 📺
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# AdCraft AI — platform API

FastAPI service behind the AdCraft AI dashboard (accounts, campaigns, audiences,
tracking, reports, recommendations, Ask Agent, Creative Studio).

The header above is Hugging Face Spaces config: this folder is pushed as the root
of a Docker Space. The Space must define the variable `PORT=7860` (matches
`app_port`) so `start.sh` binds the port the Space proxies to.

Deploy: from the repo root,

```
git subtree split --prefix api -b api-deploy
git push hf-api api-deploy:main --force
```

Health check: `GET /api/v1/health`.

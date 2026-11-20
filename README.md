# CivicConnect AI

A responsive Flask prototype for exploring Indian public schemes and services.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py app.py
```

Open http://127.0.0.1:5000. Flask creates `civicconnect.db` on first run.

Gemini integration is optional. Set `GEMINI_API_KEY` in your environment to enable generated assistant replies. Without it, chat searches the local starter directory and links to myScheme when it has no match.

## Information and privacy

The included scheme entries are starter summaries and are explicitly treated as unverified. They link to official scheme portals, but users should check current eligibility, benefits, documents, and application instructions at those sources. The eligibility form only sends a broad age and occupation value to the local backend; those values are not stored. Do not enter sensitive personal data in chat.

The language selector provides English, Kannada, and Hindi labels, with a small set of translated navigation and heading text as a prototype. Scheme records are currently English-only. Replace the starter data with reviewed, current source material before public deployment.

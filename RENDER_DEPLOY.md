# Render Deployment Guide

## Demo Deployment

This app can be deployed directly from GitHub on Render.

Repository:

`https://github.com/luckylucky110507/voice-sql-insight-agent`

## Steps

1. Sign in to Render.
2. Click `New` -> `Web Service`.
3. Connect your GitHub account if needed.
4. Select the repository:
   `voice-sql-insight-agent`
5. Confirm these settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. Click `Create Web Service`.

## Environment Variables

For demo mode, you can deploy without database variables and the app will use local SQLite sample data.

For client-ready MySQL mode, add:

- `DB_BACKEND=mysql`
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

Optional LLM planner variables:

- `LLM_API_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

## After Deployment

1. Open the Render URL.
2. Allow microphone access in Chrome or Edge.
3. Test with:
   - `Which region has the highest revenue?`
   - `Show the monthly profit trend for Alpha`
   - `What are the biggest risk hotspots?`

## Client Note

If the client wants production data instead of the sample dataset, configure the MySQL variables in the Render dashboard before sharing the live link.

# Voice-Based AI SQL Insight Agent

A voice-enabled analytics assistant that turns spoken business questions into secure SQL queries and replies with clear spoken insights, trend analysis, and risk signals through a lightweight browser interface.

## Highlights

- Voice input with browser speech-to-text
- Voice output with text-to-speech responses
- Natural language to SQL conversion with safety controls
- Context memory for follow-up questions
- Trend, anomaly, and risk-focused analytics
- Transparent SQL and returned-row visibility
- Optional LLM-backed planning with strict validation

## Why This Project

Most analytics tools still expect users to click through dashboards or write SQL manually. This project makes analytics conversational: users can ask a question out loud, see the generated query path, and receive a direct business-focused answer instead of raw data alone.

## What It Does

- Uses browser speech recognition for hands-free questions
- Converts natural-language analytics requests into read-only SQL
- Queries a local SQLite database seeded from `data/business_metrics.csv`
- Returns insight-focused answers about trends, leaders, laggards, and risk hotspots
- Supports follow-up questions by reusing conversational context
- Reads answers aloud with browser text-to-speech
- Shows the generated SQL and returned rows for transparency
- Supports an optional LLM-based query planner with strict validation and safe fallback rules

## Tech Stack

- Backend: Python, Flask, SQLite, pandas
- Frontend: HTML, CSS, vanilla JavaScript
- Voice: Web Speech API for speech-to-text and speech synthesis
- Query layer: controlled LLM planner or deterministic rule-based planner

## Project Structure

```text
.
|-- app.py
|-- src/
|   |-- agent.py
|   `-- data_setup.py
|-- templates/
|   `-- index.html
|-- static/
|   |-- app.js
|   `-- styles.css
|-- data/
|   `-- business_metrics.csv
|-- requirements.txt
|-- Procfile
`-- render.yaml
```

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the app:

```bash
python app.py
```

3. Open:

```text
http://127.0.0.1:5000
```

4. Allow microphone access in the browser to use voice mode.

## Example Questions

- `Which region has the highest revenue?`
- `Show the monthly profit trend for Alpha`
- `What are the biggest risk hotspots?`
- `What about the South region?`
- `Which product has the lowest customer satisfaction in April?`

## Security Model

- The app does not execute arbitrary user SQL
- SQL is generated only from a constrained internal schema
- LLM output is limited to a validated JSON plan, not raw SQL
- Requests are routed through whitelisted query patterns after validation
- The sample implementation is read-only and scoped to one table: `business_metrics`

## Database Schema

The sample table includes:

```text
month, region, product_line, revenue, cost, units_sold, customer_churn, csat, incident_count
```

At startup the app creates `data/voice_sql_agent.db` from the CSV file.

## How Follow-Up Context Works

Each browser session gets its own lightweight conversation memory. If the user asks a follow-up like:

- `Show the profit trend for Alpha`
- `What about North?`

the agent reuses earlier context where that makes sense.

## Deployment

### Render

This repo already includes `render.yaml`. Render can deploy it with:

```bash
python app.py
```

### Procfile-Compatible Hosts

The included `Procfile` is:

```text
web: python app.py
```

## User Guide

1. Open the application in a modern browser such as Chrome or Edge.
2. Click `Start listening` or type a question manually.
3. Review the insight summary, generated SQL, and result rows.
4. Ask a follow-up question to continue the same conversation.
5. Toggle `Voice reply` if you want silent mode.

## Customizing for a Real Client Database

To adapt this project for a production client:

1. Replace the sample CSV or point the app to the client database.
2. Extend the schema map and query templates in `src/agent.py`.
3. Configure an OpenAI-compatible planner endpoint in `src/llm_planner.py` by setting `LLM_API_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
4. Add authentication, audit logging, and stricter role-based access controls.

## Delivery Scope Alignment

This project now matches the scope you listed for freelancing:

- Voice input and voice output
- Natural language to SQL conversion with safe controls
- Context memory for follow-up questions
- Real-time trend, risk, and anomaly-oriented analysis
- Secure internal database connection pattern
- Browser-based interface
- Source code, deployment guide, and user instructions
- Python backend with an optional controlled LLM query layer

## Notes

- Browser speech recognition depends on Web Speech API support.
- The included dataset is a sample analytics dataset designed to demonstrate trends and risks.
- The repo still contains some older movie-app files from the previous project state, but they are not used by this system.

## Freelancing Materials

Reusable proposal and delivery documents are included in `freelance-kit/README.md`.

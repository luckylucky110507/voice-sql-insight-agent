from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

from src.agent import VoiceSQLAgent
from src.data_setup import describe_database, initialize_database


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
agent = VoiceSQLAgent(initialize_database())
PUBLIC_DIR = BASE_DIR / "public"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/styles.css")
def styles():
    asset_dir = PUBLIC_DIR if (PUBLIC_DIR / "styles.css").exists() else BASE_DIR / "static"
    return send_from_directory(asset_dir, "styles.css")


@app.get("/app.js")
def app_js():
    asset_dir = PUBLIC_DIR if (PUBLIC_DIR / "app.js").exists() else BASE_DIR / "static"
    return send_from_directory(asset_dir, "app.js")


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "database": describe_database(agent.db_config),
            "dbBackend": agent.db_config["backend"],
            "llmPlannerEnabled": agent.llm_planner.enabled,
        }
    )


@app.post("/api/query")
def query():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    session_id = str(payload.get("sessionId", "default-session")).strip() or "default-session"

    if not question:
        return jsonify({"error": "Please provide a question."}), 400

    result = agent.handle_query(session_id=session_id, question=question)
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

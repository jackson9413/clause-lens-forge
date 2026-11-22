"""Clause Lens - local-first contract clause reviewer.

Flask app exposing the analysis engine over a small JSON API and a single
page UI. Nothing leaves this machine: no external APIs, no LLM, no telemetry.
"""

import os

from flask import Flask, jsonify, request, send_from_directory

import engine
from engine.samples import SAMPLES, by_id
import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"), static_url_path="/static")
app.config["JSON_SORT_KEYS"] = False

MAX_CHARS = 400000


@app.after_request
def _no_store(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "engine": "clause-lens", "samples": len(SAMPLES)})


@app.route("/api/meta")
def meta():
    return jsonify({
        "contract_types": engine.CONTRACT_TYPES,
        "perspectives": [{"key": k, "label": v} for k, v in engine.PERSPECTIVES.items()],
        "samples": [{"id": s["id"], "name": s["name"], "contract_type": s["contract_type"],
                     "perspective": s["perspective"], "blurb": s["blurb"]} for s in SAMPLES],
    })


@app.route("/api/samples/<sample_id>")
def sample(sample_id):
    s = by_id(sample_id)
    if not s:
        return jsonify({"error": "unknown sample"}), 404
    return jsonify(s)


@app.route("/api/review", methods=["POST"])
def review():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text") or ""
    if not text.strip():
        return jsonify({"error": "paste a contract first"}), 400
    if len(text) > MAX_CHARS:
        return jsonify({"error": "that contract is too large (limit {0} characters)".format(MAX_CHARS)}), 400

    contract_type = payload.get("contract_type") or "generic"
    perspective = payload.get("perspective") or "party"
    title = (payload.get("title") or "").strip() or "Untitled agreement"

    result = engine.review(text, contract_type, perspective, title)
    save = payload.get("save", True)
    if save:
        try:
            result["review_id"] = db.save_review(result)
        except Exception:
            result["review_id"] = None
    return jsonify(result)


@app.route("/api/history")
def history():
    return jsonify({"reviews": db.list_reviews(limit=100)})


@app.route("/api/history/<int:review_id>", methods=["POST", "DELETE"])
def history_item(review_id):
    if request.method == "DELETE":
        if not db.get_review(review_id):
            return jsonify({"error": "not found"}), 404
        db.delete_review(review_id)
        return jsonify({"deleted": review_id})

    payload = request.get_json(silent=True) or {}
    rating = payload.get("rating")
    notes = payload.get("notes")
    if rating is not None:
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return jsonify({"error": "rating must be a number"}), 400
        if rating < 1 or rating > 5:
            return jsonify({"error": "rating must be between 1 and 5"}), 400
    if not db.rate_review(review_id, rating, notes):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/export/<int:review_id>")
def export(review_id):
    row = db.get_review(review_id)
    if not row or not row.get("result"):
        return jsonify({"error": "not found"}), 404
    result = row["result"]
    fmt = (request.args.get("format") or "md").lower()

    if fmt == "json":
        body = engine_json(result)
        return app.response_class(body, mimetype="application/json")
    if fmt == "ics":
        body = engine.to_ics(result.get("deadlines", []),
                             title=result.get("meta", {}).get("title") or "Clause Lens")
        return app.response_class(body, mimetype="text/calendar")
    body = engine.to_markdown(result)
    return app.response_class(body, mimetype="text/markdown")


def engine_json(result):
    import json
    return json.dumps(result, indent=2, ensure_ascii=False)


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(500)
def server_error(e):  # pragma: no cover - defensive
    return jsonify({"error": "server error: {0}".format(e)}), 500


def main():
    db.init_db()
    port = int(os.environ.get("PORT", "5057"))
    host = os.environ.get("HOST", "127.0.0.1")
    print("Clause Lens running on http://{0}:{1}".format(host, port))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()

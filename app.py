import os
import re
import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "civicconnect.db"
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_category(value):
    """Normalize category labels while preserving distinct category names."""
    normalized = re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
    if normalized in {"seniorcitizen", "seniorcitizens"}:
        return "seniorcitizens"
    return normalized


def official_links_for_scheme(row):
    name = row["name"].lower()
    category = normalize_category(row["category"])

    if category == "health" and "pm-jay" in name:
        return [
            {
                "label": "PM-JAY Beneficiary Portal",
                "url": "https://beneficiary.nha.gov.in/"
            }
        ]

    if category in ("seniorcitizens", "senior citizens") and "national social assistance" in name:
        return [
            {
                "label": "NSAP Scheme Information",
                "url": "https://www.myscheme.gov.in/schemes/nsap-ignoaps"
            }
        ]

    return []


CHAT_CATEGORY_TERMS = {
    "agriculture": ("farmer", "farming", "agriculture", "agricultural", "crop", "kisan"),
    "education": ("student", "scholarship", "education", "school", "college", "study"),
    "health": ("health", "medical", "hospital", "treatment", "ayushman", "pmjay", "pm-jay"),
    "seniorcitizens": ("senior", "elderly", "elder", "older", "old age", "pension", "retired", "grandfather", "grandmother", "nsap", "ignoaps"),
    "women": ("women", "woman", "ujjwala", "lpg", "cooking gas", "gas connection"),
}


def find_chat_schemes(message):
    """Find local scheme records using category hints and meaningful query terms."""
    text = re.sub(r"[^a-z0-9]+", " ", message.lower()).strip()
    with get_db() as db:
        rows = db.execute("SELECT * FROM schemes ORDER BY name").fetchall()

    def mentions(term):
        normalized_term = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
        return bool(normalized_term and re.search(r"\b" + re.escape(normalized_term) + r"\b", text))

    hinted_categories = {
        category
        for category, terms in CHAT_CATEGORY_TERMS.items()
        if any(mentions(term) for term in terms)
    }
    if hinted_categories:
        matches = [row for row in rows if normalize_category(row["category"]) in hinted_categories]
        return matches[:4]

    stop_words = {
        "a", "about", "am", "an", "and", "are", "can", "could", "do", "for", "from",
        "get", "give", "help", "how", "i", "in", "is", "it", "me", "my", "of", "please",
        "scheme", "schemes", "tell", "that", "the", "this", "to", "want", "what", "with",
    }
    terms = {term for term in text.split() if len(term) > 2 and term not in stop_words}
    scored = []
    for row in rows:
        searchable = " ".join(str(row[field] or "") for field in ("name", "category", "summary", "benefits"))
        searchable_terms = set(re.sub(r"[^a-z0-9]+", " ", searchable.lower()).split())
        score = len(terms & searchable_terms)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1]["name"]))
    return [row for _, row in scored[:4]]


def chat_scheme_context(rows):
    records = []
    for row in rows:
        records.append({
            "name": row["name"],
            "category": row["category"],
            "description": row["summary"],
            "benefits": row["benefits"],
            "eligibility": row["eligibility"],
            "required_documents": row["documents"],
            "official_links": official_links_for_scheme(row) or (
                [{"label": "Official website", "url": row["official_url"]}]
                if row["official_url"] else []
            ),
        })
    return records


def local_chat_reply(rows):
    if not rows:
        return (
            "I couldn't find a matching scheme in CivicConnect's current directory. "
            "Try mentioning the service area (such as health, education, farming, or senior citizens). "
            "You can also browse official schemes at https://www.myscheme.gov.in/."
        )

    parts = ["Here are the closest matches in CivicConnect's scheme directory:"]
    for row in rows:
        links = official_links_for_scheme(row)
        source_text = "; ".join(f"{link['label']}: {link['url']}" for link in links)
        if not source_text and row["official_url"]:
            source_text = f"Official website: {row['official_url']}"
        parts.append(
            f"{row['name']} ({row['category']})\n"
            f"Description: {row['summary']}\n"
            f"Benefits: {row['benefits']}\n"
            f"Eligibility: {row['eligibility']}\n"
            f"Required documents: {row['documents']}\n"
            f"{source_text}"
        )
    parts.append("These are starter details, not an eligibility decision. Confirm current rules with the official source.")
    return "\n\n".join(parts)


def init_db():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
            summary TEXT NOT NULL, benefits TEXT NOT NULL, eligibility TEXT NOT NULL,
            documents TEXT NOT NULL, steps TEXT NOT NULL, official_url TEXT NOT NULL,
            verified INTEGER NOT NULL DEFAULT 0
        )""")
        count = db.execute("SELECT COUNT(*) FROM schemes").fetchone()[0]
        if not count:
            # Starter examples deliberately marked unverified. Check official sources
            # and replace this data before relying on it for real applications.
            examples = [
                ("PM-KISAN", "Agriculture", "Income support scheme for eligible landholding farmer families.", "Direct income support, subject to current scheme rules.", "Eligibility depends on land records and exclusion criteria. Confirm with the official portal.", "Aadhaar, bank account details, land records (requirements may vary).", "1. Check eligibility on the official portal. 2. Complete registration through an authorized channel. 3. Track status online.", "https://pmkisan.gov.in/"),
                ("National Scholarship Portal", "Education", "A government portal where students can find and apply for participating scholarships.", "Scholarship benefits vary by the individual scheme.", "Criteria vary by scholarship, course, institution, income, and other rules. Check the relevant notice.", "Commonly requested items may include Aadhaar, income/caste certificates, marksheets, and bank details; verify the specific scheme.", "1. Find a scholarship on the portal. 2. Read its current guidelines. 3. Apply and track the application.", "https://scholarships.gov.in/"),
                ("Ayushman Bharat PM-JAY", "Health", "Public health coverage programme for eligible families.", "Hospitalization coverage under programme terms and approved providers.", "Eligibility is determined through official beneficiary records; check the official portal or helpline.", "Beneficiary identification documents; confirm requirements with an authorized help desk.", "1. Check beneficiary status. 2. Visit an authorized help desk if needed. 3. Follow the official process for an e-card.", "https://pmjay.gov.in/"),
                ("National Social Assistance Programme", "Senior citizens", "Social assistance programmes for eligible older persons and other groups.", "Assistance and amounts depend on the specific component and state rules.", "Age, income, and other criteria vary; confirm current central and state requirements.", "Identity, age, residence, income and bank documents may be requested. Verify locally.", "1. Identify the applicable component. 2. Confirm state requirements. 3. Apply through the designated local office or portal.", "https://nsap.nic.in/"),
                ("PM Ujjwala Yojana", "Women", "LPG connection scheme for eligible households, subject to current guidelines.", "Benefits and connection support are subject to scheme rules.", "Eligibility and application conditions can change. Confirm with the official portal or an authorized distributor.", "Identity, address, household and eligibility documents as required by current guidelines.", "1. Check the latest eligibility rules. 2. Apply through an authorized LPG distributor or official channel. 3. Track application status.", "https://www.pmuy.gov.in/"),
            ]
            db.executemany("INSERT INTO schemes (name,category,summary,benefits,eligibility,documents,steps,official_url,verified) VALUES (?,?,?,?,?,?,?,?,0)", examples)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/schemes")
def schemes():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    sql = "SELECT * FROM schemes WHERE 1=1"
    params = []

    if query:
        sql += " AND (name LIKE ? OR summary LIKE ? OR category LIKE ?)"
        params.extend([f"%{query}%"] * 3)

    sql += " ORDER BY name"

    with get_db() as db:
        rows = db.execute(sql, params).fetchall()

    if category and category.strip().lower() != "all categories":
        wanted_category = normalize_category(category)
        rows = [row for row in rows if normalize_category(row["category"]) == wanted_category]

    results = []
    for row in rows:
        scheme = dict(row)
        scheme["official_links"] = official_links_for_scheme(row)
        if scheme["official_links"]:
            scheme["official_url"] = scheme["official_links"][0]["url"]
        results.append(scheme)

    return jsonify(results)


@app.post("/api/eligibility")
def eligibility():
    payload = request.get_json(silent=True) or {}
    age = payload.get("age")
    occupation = str(payload.get("occupation", "")).strip().lower()
    # The prototype avoids retaining submitted details and does not make
    # eligibility determinations without authoritative, current rule data.
    suggestions = []
    with get_db() as db:
        rows = db.execute("SELECT id,name,category,summary,official_url FROM schemes").fetchall()
    for row in rows:
        category = row["category"].lower()
        relevant = ("farmer" in occupation and category == "agriculture") or (age and int(age) >= 60 and category == "senior citizens") or ("student" in occupation and category == "education") or (not occupation)
        if relevant:
            suggestions.append(dict(row))
    return jsonify({"message": "These are starting points only. This prototype cannot confirm eligibility. Check the current official rules before applying.", "suggestions": suggestions})


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = str(payload.get("message", "")).strip()

    if not message:
        return jsonify({"reply": "Tell me what service or scheme you want to learn about."})

    if message.lower() in ["hi", "hello", "hey", "good morning", "good afternoon"]:
        return jsonify({"reply": "Hello! Welcome to CivicConnect AI. I can help you find government schemes, check eligibility, and understand required documents. How can I help you today?"})

    matches = find_chat_schemes(message)
    return jsonify({"reply": local_chat_reply(matches)})
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=10000)
                )
            context = json.dumps(chat_scheme_context(matches), ensure_ascii=False)
            result = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                contents=(
                    "You are CivicConnect, a clear and cautious guide to the schemes in the supplied project data. "
                    "Answer the user's question using only the supplied records. Do not add outside facts, guess, "
                    "infer eligibility, or invent benefits, documents, deadlines, or URLs. If a detail is absent, "
                    "say the directory does not specify it and point to the supplied official link. Keep the answer "
                    "concise and relevant. Do not request personal or sensitive information.\n\n"
                    f"Project scheme records (JSON): {context}\n\nUser question: {message}"
                ),
            )
            if result.text:
                return jsonify({"reply": result.text})
        except Exception:
            app.logger.exception("Gemini request failed")
    return jsonify({"reply": local_chat_reply(matches)})


@app.get("/api/categories")
def categories():
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT category FROM schemes ORDER BY category").fetchall()
    return jsonify([r[0] for r in rows])


init_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")

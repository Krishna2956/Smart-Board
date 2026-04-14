from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3, threading, time, logging
from datetime import datetime, date

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
DB = "notices.db"

# ── DATABASE ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                category    TEXT    DEFAULT 'Other',
                deadline    TEXT    DEFAULT '',
                eligibility TEXT    DEFAULT '',
                location    TEXT    DEFAULT '',
                link        TEXT    DEFAULT '',
                source      TEXT    DEFAULT 'Manual',
                description TEXT    DEFAULT '',
                prize       TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now')),
                is_expired  INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_log (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                ran_at   TEXT DEFAULT (datetime('now')),
                added    INTEGER DEFAULT 0
            )
        """)
        conn.commit()
    seed_data()
    mark_expired()

def seed_data():
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0:
            return
        events = [
            ("Smart India Hackathon 2025",       "Hackathon",   "2025-09-15", "B.Tech / M.Tech students",          "Pan India (Online + Offline)", "https://sih.gov.in",                          "SIH Portal",   "India's biggest national-level hackathon by Govt of India. Solve real problems for ministries and PSUs.",                         "₹1,00,000"),
            ("Google Summer of Code 2025",        "Internship",  "2025-04-08", "Open-source contributors 18+",      "Remote (Worldwide)",           "https://summerofcode.withgoogle.com",          "Google",       "Paid open-source internship program. Work with top open-source organizations for 3 months.",                                       "$3,000 – $6,600"),
            ("Microsoft Imagine Cup 2025",         "Hackathon",   "2025-05-01", "Students worldwide",                "Online + Seattle Finals",      "https://imaginecup.microsoft.com",             "Microsoft",    "Global student technology competition. Build AI and cloud-powered solutions to change the world.",                                "₹80,00,000+"),
            ("Amazon ML Challenge 2025",           "Hackathon",   "2025-06-30", "UG / PG students",                  "Online",                       "https://www.hackerearth.com/challenges/",      "Amazon",       "Machine learning problem-solving contest by Amazon. Top performers receive direct interview calls.",                              "₹5,00,000"),
            ("Flipkart GRiD 6.0",                  "Hackathon",   "2025-07-20", "Engineering students",              "Online + Bengaluru Finals",    "https://unstop.com/competitions/flipkart-grid","Flipkart",     "E-commerce and tech innovation challenge by Flipkart. Top teams get to visit Flipkart HQ.",                                        "₹5,00,000"),
            ("TCS CodeVita Season 13",             "Hackathon",   "2025-08-15", "Engineering students",              "Online",                       "https://tcs.com/codevita",                     "TCS",          "World's largest coding contest. Multiple rounds. Winners receive a TCS job offer.",                                              "Job Offer + ₹5,00,000"),
            ("HackWithInfy 2025",                  "Hackathon",   "2025-07-01", "Engineering students",              "Online",                       "https://infosys.com/hackwithinfy",             "Infosys",      "3-round competitive coding and innovation contest by Infosys. Top scorers get direct job offer.",                                 "Job Offer + ₹5,00,000"),
            ("Google Kick Start 2025",             "Hackathon",   "2025-05-12", "All programmers",                   "Online",                       "https://codingcompetitions.withgoogle.com",   "Google",       "Competitive programming rounds organized by Google. Multiple rounds conducted throughout the year.",                             "Google Swag + Recognition"),
            ("NASSCOM AI Gamechangers",            "Hackathon",   "2025-08-01", "Students and professionals",        "Online",                       "https://nasscom.in",                          "NASSCOM",      "AI/ML focused national-level hackathon. Build AI solutions for social good and sustainability.",                                  "₹3,00,000"),
            ("HackerEarth University Hack",        "Hackathon",   "2025-05-10", "All college students",              "Online",                       "https://hackerearth.com",                     "HackerEarth",  "National online hackathon with multiple problem tracks. Weekly coding challenges with cash prizes.",                              "₹2,00,000"),
            ("CodeChef Starters Weekly",           "Hackathon",   "2025-05-07", "All programmers",                   "Online",                       "https://codechef.com/START",                  "CodeChef",     "Weekly rated coding contests on CodeChef. Great way to improve competitive programming rating.",                                  "Rating + Prizes"),
            ("CVR Hackathon 3.0",                  "Hackathon",   "2025-05-30", "CVR College students",              "CVR College Campus",           "#",                                           "CVR Tech Club","24-hour on-campus hackathon. Build innovative solutions for real-world problems within 24 hours.",                               "₹50,000 + Internship"),
            ("Infosys InStep Internship 2025",     "Internship",  "2025-06-01", "Pre-final year, 7+ CGPA",           "Pune / Bengaluru / Hyderabad", "https://infosys.com/instep",                  "Infosys",      "International internship program by Infosys. Work on live client projects with global teams.",                                    "₹25,000/month"),
            ("Goldman Sachs Engineering Intern",   "Internship",  "2025-05-15", "CS/IT 3rd year, 7+ CGPA",           "Bengaluru / Hyderabad",        "https://goldmansachs.com/careers",            "Goldman Sachs","Software Engineering internship with PPO opportunity for top performers.",                                                    "₹80,000/month"),
            ("Internshala Web Dev Internship",     "Internship",  "2025-06-15", "Any student",                       "Remote",                       "https://internshala.com",                     "Internshala",  "2-month work-from-home web development internship. Work on real client projects.",                                              "₹5,000–15,000/month"),
            ("AWS Cloud Practitioner Bootcamp",    "Workshop",    "2025-05-25", "All students",                      "Online (Zoom)",                "https://aws.amazon.com/training",             "AWS",          "Free 2-day cloud bootcamp by Amazon Web Services. Receive AWS Cloud Practitioner exam voucher.",                                   "Free + Exam Voucher"),
            ("Python Flask & REST API Workshop",   "Workshop",    "2025-05-05", "All CSE students",                  "CVR Seminar Hall A",           "#",                                           "CVR CSE Dept", "3-day hands-on workshop covering Python, Flask, REST APIs, SQLite and project deployment.",                                      "Certificate"),
            ("GATE 2026 Preparation Seminar",      "Academic",    "2025-05-20", "Final year B.Tech students",        "CVR Main Auditorium",          "#",                                           "CVR Training", "Expert-led GATE 2026 preparation seminar with mock tests, tips and free study material.",                                        "Free"),
            ("National Science Day Poster Comp",   "Academic",    "2025-05-28", "All UG students",                   "CVR Science Block",            "#",                                           "CVR Science",  "Poster competition on the theme 'Science for Sustainable Future'. Open to all UG students.",                                    "₹5,000"),
            ("Inter-College Cricket Tournament",   "Sports",      "2025-06-10", "CVR College students",              "CVR Sports Ground",            "#",                                           "CVR Sports",   "Annual inter-college cricket championship. Register your team of 11 players before deadline.",                                  "Trophy + ₹10,000"),
        ]
        conn.executemany(
            "INSERT INTO events(title,category,deadline,eligibility,location,link,source,description,prize) VALUES(?,?,?,?,?,?,?,?,?)",
            events
        )
        conn.commit()
        log.info("Seeded %d events.", len(events))

def mark_expired():
    today = date.today().isoformat()
    with get_db() as conn:
        conn.execute("UPDATE events SET is_expired=1 WHERE deadline!='' AND deadline IS NOT NULL AND deadline < ?", (today,))
        conn.commit()

# ── SCRAPER (optional background job) ────────────────────────────────────────

def scrape():
    added = 0
    try:
        import requests as req
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (compatible; SmartNoticeBot/1.0)"}
        r = req.get("https://devpost.com/hackathons?open_to[]=public", headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".hackathon-tile")[:6]:
            t = card.select_one("h3")
            a = card.select_one("a")
            if t and a:
                title = t.get_text(strip=True)
                link  = a.get("href", "")
                with get_db() as conn:
                    if not conn.execute("SELECT id FROM events WHERE title=?", (title,)).fetchone():
                        conn.execute(
                            "INSERT INTO events(title,category,location,link,source,description,prize) VALUES(?,?,?,?,?,?,?)",
                            (title, "Hackathon", "Online", link, "Devpost", "Hackathon listed on Devpost.", "Varies")
                        )
                        conn.commit()
                        added += 1
    except Exception as e:
        log.warning("Scraper error: %s", e)

    mark_expired()
    with get_db() as conn:
        conn.execute("INSERT INTO scrape_log(added) VALUES(?)", (added,))
        conn.commit()
    log.info("Scrape complete. Added %d new events.", added)
    return added

def background_scheduler():
    while True:
        try:
            scrape()
        except Exception as e:
            log.error("Scheduler error: %s", e)
        time.sleep(6 * 3600)

# ── API ROUTES ────────────────────────────────────────────────────────────────

@app.route("/api/events", methods=["GET"])
def get_events():
    category    = request.args.get("category", "")
    search      = request.args.get("search", "")
    show_exp    = request.args.get("expired", "false").lower() == "true"
    page        = max(1, int(request.args.get("page", 1)))
    limit       = int(request.args.get("limit", 12))
    offset      = (page - 1) * limit

    q = "SELECT * FROM events WHERE 1=1"
    params = []

    if not show_exp:
        q += " AND is_expired = 0"
    if category and category != "All":
        q += " AND category = ?"
        params.append(category)
    if search:
        q += " AND (title LIKE ? OR description LIKE ? OR eligibility LIKE ? OR source LIKE ? OR prize LIKE ?)"
        params += [f"%{search}%"] * 5

    count_q = q.replace("SELECT *", "SELECT COUNT(*)")
    total   = get_db().execute(count_q, params).fetchone()[0]

    q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    rows   = get_db().execute(q, params).fetchall()
    events = [dict(r) for r in rows]

    return jsonify({
        "events": events,
        "total":  total,
        "page":   page,
        "pages":  max(1, -(-total // limit))
    })


@app.route("/api/events/<int:eid>", methods=["GET"])
def get_event(eid):
    row = get_db().execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


@app.route("/api/events", methods=["POST"])
def create_event():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    if not data.get("title", "").strip():
        return jsonify({"error": "Title is required"}), 400

    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO events
               (title, category, deadline, eligibility, location, link, source, description, prize)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["title"].strip(),
                data.get("category", "Other"),
                data.get("deadline", ""),
                data.get("eligibility", ""),
                data.get("location", ""),
                data.get("link", ""),
                data.get("source", "Manual"),
                data.get("description", ""),
                data.get("prize", ""),
            )
        )
        conn.commit()
        new_id = cur.lastrowid

    return jsonify({"id": new_id, "message": "Event created successfully"}), 201


@app.route("/api/events/<int:eid>", methods=["DELETE"])
def delete_event(eid):
    with get_db() as conn:
        conn.execute("DELETE FROM events WHERE id=?", (eid,))
        conn.commit()
    return jsonify({"message": "Deleted"})


@app.route("/api/categories", methods=["GET"])
def get_categories():
    rows = get_db().execute(
        "SELECT category, COUNT(*) as cnt FROM events WHERE is_expired=0 GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    return jsonify([{"name": r["category"], "count": r["cnt"]} for r in rows])


@app.route("/api/stats", methods=["GET"])
def get_stats():
    d = get_db()
    return jsonify({
        "active":  d.execute("SELECT COUNT(*) FROM events WHERE is_expired=0").fetchone()[0],
        "expired": d.execute("SELECT COUNT(*) FROM events WHERE is_expired=1").fetchone()[0],
        "total":   d.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "scrapes": d.execute("SELECT COUNT(*) FROM scrape_log").fetchone()[0],
        "last":    (d.execute("SELECT ran_at FROM scrape_log ORDER BY id DESC LIMIT 1").fetchone() or [None])[0],
    })


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    n = scrape()
    return jsonify({"message": f"Scrape complete. {n} new events added."})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat(), "events": get_db().execute("SELECT COUNT(*) FROM events").fetchone()[0]})


@app.route("/", methods=["GET"])
def root():
    return jsonify({"message": "Smart Notice Board API v2.0", "health": "/api/health", "events": "/api/events"})


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    threading.Thread(target=background_scheduler, daemon=True).start()
    app.run(debug=True, host="0.0.0.0", port=5000)
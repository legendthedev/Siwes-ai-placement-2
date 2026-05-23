"""
seed_tech_schools.py
─────────────────────────────────────────────────────────────────────────────
Pre-registers top tech schools across Lagos, Abuja, Ibadan, Calabar, Kwara.

Each school receives a User account (role="admin") with default password:
    Siwes@<SchoolFirstWord>2024
    e.g.  AltSchool Africa  →  Siwes@AltSchool2024
          Semicolon Africa  →  Siwes@Semicolon2024

The school admin can log in to:
  • View students who enrolled after passing their preliminary test
  • See test scores and enrollment status
  • Confirm payment / mark students as enrolled

Only students who selected track="tech_school" during registration
and PASSED the preliminary test (≥ 60%) can submit an enrollment request.
─────────────────────────────────────────────────────────────────────────────
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal, init_db, engine
from models import TechSchool, SchoolCourse, PreliminaryQuestion, User
from sqlalchemy import text


def _default_password(school_name: str) -> str:
    word = re.split(r"[\s\-/(]", school_name.strip())[0]
    return f"Siwes@{word}2024"


SCHOOLS = [
    # ══════════════════════════════════════
    # LAGOS
    # ══════════════════════════════════════
    {
        "school": {
            "name": "AltSchool Africa",
            "state": "Lagos",
            "location": "Yaba, Lagos",
            "website": "https://altschoolafrica.com",
            "description": "Africa-focused tech school offering online and hybrid engineering programmes.",
            "siwes_discount_pct": 15,
            "siwes_discount_note": "15% off for SIWES-registered students on presentation of ITF letter.",
        },
        "courses": [
            {"name":"Frontend Engineering","duration_months":12,"price_ngn":360000,
             "skills":["html","css","javascript","react","git","typescript","nextjs"],
             "description":"Full frontend track from HTML to production-grade React apps."},
            {"name":"Backend Engineering","duration_months":12,"price_ngn":360000,
             "skills":["python","nodejs","postgresql","rest api","docker","git"],
             "description":"Backend fundamentals to cloud deployment."},
            {"name":"Data Science & ML","duration_months":12,"price_ngn":380000,
             "skills":["python","machine learning","pandas","numpy","scikit-learn","sql"],
             "description":"From Python basics to production machine learning models."},
        ]
    },
    {
        "school": {
            "name": "Semicolon Africa",
            "state": "Lagos",
            "location": "Yaba, Lagos",
            "website": "https://semicolon.africa",
            "description": "Immersive software engineering school focused on product development.",
            "siwes_discount_pct": 10,
            "siwes_discount_note": "10% SIWES tuition reduction; apply via admissions portal.",
        },
        "courses": [
            {"name":"Software Engineering","duration_months":12,"price_ngn":480000,
             "skills":["java","javascript","react","nodejs","postgresql","git","agile","oop"],
             "description":"Intensive product engineering training with real client projects."},
        ]
    },
    {
        "school": {
            "name": "Decagon Institute",
            "state": "Lagos",
            "location": "Lekki, Lagos",
            "website": "https://decagoninstitute.com",
            "description": "Software engineering fellowship preparing candidates for global tech roles.",
            "siwes_discount_pct": 20,
            "siwes_discount_note": "20% off programme fee for SIWES applicants. Contact admissions.",
        },
        "courses": [
            {"name":"Software Engineering Fellowship","duration_months":6,"price_ngn":250000,
             "skills":["javascript","python","java","react","nodejs","postgresql","git","algorithms"],
             "description":"Six-month intensive fellowship with job placement support."},
        ]
    },
    {
        "school": {
            "name": "HiiT Plc (Lagos)",
            "state": "Lagos",
            "location": "Ikeja, Lagos",
            "website": "https://hiitplc.com",
            "description": "One of Nigeria's longest-running ICT training institutions.",
            "siwes_discount_pct": 10,
            "siwes_discount_note": "10% SIWES discount on selected courses with valid student ID.",
        },
        "courses": [
            {"name":"Cybersecurity & Ethical Hacking","duration_months":6,"price_ngn":180000,
             "skills":["cybersecurity","networking","linux","penetration testing","wireshark","python"],
             "description":"Practical cybersecurity training from fundamentals to CEH level."},
            {"name":"Cloud Computing (AWS)","duration_months":4,"price_ngn":150000,
             "skills":["aws","linux","docker","networking","bash","cloud computing"],
             "description":"AWS Solutions Architect Associate preparation."},
        ]
    },

    # ══════════════════════════════════════
    # ABUJA
    # ══════════════════════════════════════
    {
        "school": {
            "name": "Codetrain Abuja",
            "state": "Abuja",
            "location": "Wuse 2, Abuja",
            "website": "https://codetrain.africa",
            "description": "Pan-African coding bootcamp with campus in Abuja.",
            "siwes_discount_pct": 15,
            "siwes_discount_note": "SIWES students receive 15% discount. Apply with ITF registration.",
        },
        "courses": [
            {"name":"Full Stack Web Development","duration_months":9,"price_ngn":290000,
             "skills":["javascript","react","nodejs","postgresql","git","rest api","css"],
             "description":"Job-ready full stack training with portfolio projects."},
            {"name":"Data Science","duration_months":9,"price_ngn":310000,
             "skills":["python","pandas","machine learning","sql","numpy","scikit-learn"],
             "description":"Applied data science with Nigerian business case studies."},
        ]
    },
    {
        "school": {
            "name": "NIIT Abuja",
            "state": "Abuja",
            "location": "Garki 2, Abuja",
            "website": "https://niit.com.ng",
            "description": "Global tech training institute with extensive Nigerian presence.",
            "siwes_discount_pct": 10,
            "siwes_discount_note": "10% off for SIWES students on any programme.",
        },
        "courses": [
            {"name":"Mobile App Development (Android)","duration_months":6,"price_ngn":160000,
             "skills":["android","kotlin","java","firebase","rest api","git"],
             "description":"Build and publish Android applications."},
            {"name":"Networking & CCNA","duration_months":6,"price_ngn":140000,
             "skills":["networking","cisco","linux","wireshark","bash","tcp/ip"],
             "description":"Cisco Certified Network Associate preparation."},
        ]
    },

    # ══════════════════════════════════════
    # IBADAN
    # ══════════════════════════════════════
    {
        "school": {
            "name": "Ingressive For Good (I4G) Ibadan",
            "state": "Ibadan",
            "location": "UI Campus, Ibadan",
            "website": "https://ingressive4good.org",
            "description": "Not-for-profit tech training empowering African youth.",
            "siwes_discount_pct": 25,
            "siwes_discount_note": "25% SIWES bursary available. Apply via scholarship portal.",
        },
        "courses": [
            {"name":"Frontend Development","duration_months":6,"price_ngn":80000,
             "skills":["html","css","javascript","react","git","typescript"],
             "description":"Affordable frontend track with mentorship."},
            {"name":"Backend Development (Python)","duration_months":6,"price_ngn":80000,
             "skills":["python","django","postgresql","rest api","git","linux"],
             "description":"Backend development with Django and PostgreSQL."},
        ]
    },
    {
        "school": {
            "name": "Tech Hub Ibadan",
            "state": "Ibadan",
            "location": "Challenge, Ibadan",
            "website": "https://techhibadan.ng",
            "description": "Oyo State's foremost tech skill development hub.",
            "siwes_discount_pct": 15,
            "siwes_discount_note": "15% off for enrolled SIWES students.",
        },
        "courses": [
            {"name":"UI/UX Design & Prototyping","duration_months":4,"price_ngn":95000,
             "skills":["figma","ui/ux design","user research","prototyping","css","javascript"],
             "description":"Design thinking to Figma prototyping."},
        ]
    },

    # ══════════════════════════════════════
    # CALABAR
    # ══════════════════════════════════════
    {
        "school": {
            "name": "Calabar Tech Hub Academy",
            "state": "Calabar",
            "location": "Efio-Ette, Calabar",
            "website": "https://calabarhub.ng/academy",
            "description": "Cross River State's primary coding and digital skills academy.",
            "siwes_discount_pct": 20,
            "siwes_discount_note": "20% SIWES discount with valid ITF letter.",
        },
        "courses": [
            {"name":"Web Development Bootcamp","duration_months":6,"price_ngn":120000,
             "skills":["html","css","javascript","react","git","nodejs","rest api"],
             "description":"Hands-on web development with local industry projects."},
            {"name":"Digital Marketing & Analytics","duration_months":3,"price_ngn":75000,
             "skills":["google analytics","seo","social media","data analysis","excel"],
             "description":"Digital marketing fundamentals with analytics tools."},
        ]
    },

    # ══════════════════════════════════════
    # KWARA
    # ══════════════════════════════════════
    {
        "school": {
            "name": "Ilorin Tech Academy (iTA)",
            "state": "Kwara",
            "location": "University Road, Ilorin",
            "website": "https://ilorintechacademy.ng",
            "description": "North-Central Nigeria's leading technology training institution.",
            "siwes_discount_pct": 15,
            "siwes_discount_note": "15% off all programmes for SIWES-registered students.",
        },
        "courses": [
            {"name":"Full Stack JavaScript","duration_months":8,"price_ngn":175000,
             "skills":["javascript","react","nodejs","mongodb","git","rest api","css"],
             "description":"MERN stack development with project portfolio."},
            {"name":"Data Analytics","duration_months":4,"price_ngn":110000,
             "skills":["python","pandas","sql","excel","tableau","data analysis"],
             "description":"Business data analysis using Python and Tableau."},
        ]
    },
]

# ── Preliminary test question bank per skill domain ──────────────────────────

QUESTION_BANK = {
    "javascript": [
        {"question":"What is the output of: typeof null", "options":["null","object","undefined","string"], "answer":"object", "points":2},
        {"question":"Which method converts JSON string to object?", "options":["JSON.parse()","JSON.stringify()","JSON.convert()","JSON.decode()"], "answer":"JSON.parse()", "points":2},
        {"question":"What does === check in JavaScript?", "options":["Value only","Type only","Value and type","Reference"], "answer":"Value and type", "points":2},
    ],
    "python": [
        {"question":"What is the output of: print(type([]))?", "options":["<class 'list'>","list","array","<list>"], "answer":"<class 'list'>", "points":2},
        {"question":"Which keyword defines a function in Python?", "options":["function","def","fun","define"], "answer":"def", "points":2},
        {"question":"What does len([1,2,3]) return?", "options":["2","3","4","1"], "answer":"3", "points":2},
    ],
    "react": [
        {"question":"What hook is used for state in React functional components?", "options":["useEffect","useState","useRef","useContext"], "answer":"useState", "points":2},
        {"question":"What does JSX stand for?", "options":["JavaScript XML","JavaScript Extension","Java Syntax Extension","JavaScript Extra"], "answer":"JavaScript XML", "points":2},
    ],
    "sql": [
        {"question":"Which SQL clause filters rows?", "options":["ORDER BY","GROUP BY","WHERE","HAVING"], "answer":"WHERE", "points":2},
        {"question":"What does SELECT DISTINCT do?", "options":["Selects all rows","Removes duplicate rows","Sorts results","Counts rows"], "answer":"Removes duplicate rows", "points":2},
    ],
    "networking": [
        {"question":"What does DNS stand for?", "options":["Domain Name System","Data Network Service","Digital Name Server","Domain Network Standard"], "answer":"Domain Name System", "points":2},
        {"question":"Which protocol is used for secure web browsing?", "options":["HTTP","FTP","HTTPS","SMTP"], "answer":"HTTPS", "points":2},
    ],
    "cybersecurity": [
        {"question":"What is a SQL injection?", "options":["A hardware attack","Injecting malicious SQL into input fields","A network attack","A phishing attack"], "answer":"Injecting malicious SQL into input fields", "points":2},
        {"question":"What does VPN stand for?", "options":["Virtual Private Network","Virtual Public Network","Verified Private Node","Virtual Protocol Network"], "answer":"Virtual Private Network", "points":2},
    ],
    "machine learning": [
        {"question":"What is overfitting?", "options":["Model performs well on training, poorly on test","Model performs well on both","Model is too simple","Model has no training data"], "answer":"Model performs well on training, poorly on test", "points":2},
        {"question":"Which algorithm is used for classification?", "options":["Linear Regression","K-Means","Logistic Regression","PCA"], "answer":"Logistic Regression", "points":2},
    ],
    "general_aptitude": [
        {"question":"A loop that runs forever is called a(n) ___ loop.", "options":["infinite","endless","dead","null"], "answer":"infinite", "points":1},
        {"question":"What is an algorithm?", "options":["A programming language","A step-by-step problem-solving procedure","A database","A hardware component"], "answer":"A step-by-step problem-solving procedure", "points":1},
        {"question":"Binary number 1010 equals which decimal?", "options":["8","10","12","14"], "answer":"10", "points":2},
        {"question":"What does RAM stand for?", "options":["Random Access Memory","Read Access Memory","Rapid Access Module","Remote Access Memory"], "answer":"Random Access Memory", "points":1},
    ],
}


# ── Seed function ─────────────────────────────────────────────────────────────
def seed_tech_schools():
    """Insert tech schools with User accounts, courses and test questions."""
    init_db()
    _ensure_user_id_col()

    db = SessionLocal()
    added_s = added_c = added_q = 0
    credentials = []

    try:
        for entry in SCHOOLS:
            s_data     = entry["school"]
            default_pw = _default_password(s_data["name"])
            email      = s_data.get("email") or _derive_email(s_data["name"])

            # ── User account ──────────────────────────────────────────────
            user = db.query(User).filter_by(email=email).first()
            if not user:
                user = User(email=email, role="admin")
                user.set_password(default_pw)
                db.add(user)
                db.flush()

            # ── School record ─────────────────────────────────────────────
            school = db.query(TechSchool).filter_by(name=s_data["name"]).first()
            if school:
                if school.user_id is None:
                    school.user_id       = user.id
                    school.contact_email = email
                print(f"[SKIP] {s_data['name']} already exists")
            else:
                school = TechSchool(
                    user_id=user.id,
                    name=s_data["name"],
                    state=s_data["state"],
                    location=s_data["location"],
                    website=s_data.get("website",""),
                    description=s_data.get("description",""),
                    siwes_discount_pct=s_data.get("siwes_discount_pct", 0),
                    siwes_discount_note=s_data.get("siwes_discount_note",""),
                    contact_email=email,
                )
                db.add(school)
                db.flush()
                added_s += 1
                credentials.append({
                    "school":   s_data["name"],
                    "email":    email,
                    "password": default_pw,
                    "state":    s_data["state"],
                })
                print(f"[OK] {s_data['name']} ({s_data['state']})  pw={default_pw}")

            # ── Courses + questions ────────────────────────────────────────
            for c_data in entry["courses"]:
                ex = db.query(SchoolCourse).filter_by(
                    school_id=school.id, name=c_data["name"]).first()
                if ex:
                    continue

                discount   = school.siwes_discount_pct or 0
                siwes_price = int(c_data["price_ngn"] * (1 - discount / 100))

                course = SchoolCourse(
                    school_id=school.id,
                    name=c_data["name"],
                    duration_months=c_data["duration_months"],
                    price_ngn=c_data["price_ngn"],
                    siwes_price_ngn=siwes_price,
                    description=c_data.get("description",""),
                )
                course.set_skills(c_data["skills"])
                db.add(course)
                db.flush()
                added_c += 1

                # Seed test questions
                primary_skills = c_data["skills"][:2] + ["general_aptitude"]
                seen = set()
                for skill in primary_skills:
                    for q in QUESTION_BANK.get(skill, []):
                        key = q["question"]
                        if key in seen:
                            continue
                        seen.add(key)
                        db.add(PreliminaryQuestion(
                            course_id=course.id,
                            question=q["question"],
                            options=json.dumps(q["options"]),
                            correct_answer=q["answer"],
                            points=q["points"],
                            skill_domain=skill,
                        ))
                        added_q += 1

        db.commit()

        # ── Print credentials ─────────────────────────────────────────────
        if credentials:
            print("\n" + "═" * 72)
            print("  DEFAULT TECH SCHOOL ADMIN CREDENTIALS (change on first login)")
            print("═" * 72)
            for c in credentials:
                print(f"  {c['school']:<35} {c['email']}")
                print(f"  {'':<35} Password: {c['password']}")
                print()
            print("═" * 72)

        print(f"\n✅ {added_s} schools · {added_c} courses · {added_q} questions seeded.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


def _derive_email(school_name: str) -> str:
    """Derive a contact email from the school name."""
    slug = re.sub(r"[^a-z0-9]", "", school_name.lower().split()[0])
    return f"admissions@{slug}.ng"


def _ensure_user_id_col():
    """Add user_id and contact_email columns to tech_schools if missing."""
    with engine.connect() as conn:
        for col in ["user_id INTEGER", "contact_email VARCHAR(120)"]:
            try:
                conn.execute(text(f"ALTER TABLE tech_schools ADD COLUMN {col}"))
                conn.commit()
            except Exception:
                pass


if __name__ == "__main__":
    seed_tech_schools()

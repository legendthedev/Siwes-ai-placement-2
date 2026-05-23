"""
seed_companies_extended.py
─────────────────────────────────────────────────────────────────────────────
Pre-registers real tech companies across Lagos, Abuja, Ibadan, Calabar, Kwara.

Each company receives a User account (role="admin") with a default password:
    Siwes@<CompanyFirstWord>2024
    e.g.  Flutterwave → Siwes@Flutterwave2024
          Paystack    → Siwes@Paystack2024

After seeding, credentials are printed to the console.
All companies are set verified=True so they appear in the placement algorithm.

Quota reduction:
    Call reduce_quotas_after_placement(batch_id) after any placement run to
    decrement each JD's remaining_quota by the number of students placed there.
─────────────────────────────────────────────────────────────────────────────
"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import SessionLocal, init_db, engine
from models import Company, JobDescription, User, Placement
from sqlalchemy import text


def _default_password(company_name: str) -> str:
    """Derive a deterministic default password from the company name."""
    word = re.split(r"[\s\-/(]", company_name.strip())[0]   # first word only
    return f"Siwes@{word}2024"


COMPANIES = [
    # ══════════════════════════════════════
    # LAGOS
    # ══════════════════════════════════════
    {
        "company": {"name":"Flutterwave","email":"internships@flutterwave.com",
                    "industry":"Fintech","location":"Lekki, Lagos","state":"Lagos",
                    "website":"https://flutterwave.com",
                    "description":"Africa's leading payments technology company."},
        "jds":[
            {"title":"Backend Engineering Intern","quota":4,"target_department":"Computer Science / Software Engineering",
             "location":"Lekki, Lagos","required_skills":["python","nodejs","rest api","postgresql","git","docker","microservices","algorithms"],
             "raw_text":"Build and maintain payment APIs using Python or Node.js, PostgreSQL, Docker. Quota: 4."},
            {"title":"Data Analytics Intern","quota":2,"target_department":"Computer Science / IT",
             "location":"Lekki, Lagos","required_skills":["python","pandas","numpy","sql","tableau","data analysis","excel"],
             "raw_text":"Analyse transaction trends using Python, SQL, Tableau. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Interswitch Group","email":"internship@interswitchgroup.com",
                    "industry":"Payment Technology","location":"Victoria Island, Lagos","state":"Lagos",
                    "website":"https://www.interswitchgroup.com",
                    "description":"Pioneer African payments and digital commerce company."},
        "jds":[
            {"title":"Java Backend Intern","quota":4,"target_department":"Computer Science / Software Engineering",
             "location":"Victoria Island, Lagos","required_skills":["java","spring boot","postgresql","oracle","rest api","git","microservices"],
             "raw_text":"Build transactional microservices in Java/Spring Boot. Quota: 4."},
            {"title":"Cloud/DevOps Intern","quota":2,"target_department":"Computer Engineering",
             "location":"Victoria Island, Lagos","required_skills":["aws","docker","kubernetes","linux","ci/cd","terraform","python"],
             "raw_text":"Automate AWS infrastructure, manage K8s. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Andela Nigeria","email":"talent@andela.com",
                    "industry":"Tech Engineering","location":"Yaba, Lagos","state":"Lagos",
                    "website":"https://andela.com",
                    "description":"Global platform training and connecting African software engineers."},
        "jds":[
            {"title":"Full Stack Engineering Intern","quota":5,"target_department":"Computer Science / Software Engineering",
             "location":"Yaba, Lagos","required_skills":["javascript","typescript","react","nodejs","postgresql","rest api","git","docker"],
             "raw_text":"Build internal tools using TypeScript, React, Node.js. Quota: 5."},
        ]
    },
    {
        "company": {"name":"Moniepoint (TeamApt)","email":"siwes@moniepoint.com",
                    "industry":"Fintech","location":"Yaba, Lagos","state":"Lagos",
                    "website":"https://moniepoint.com",
                    "description":"Powers payments and banking for Nigerian businesses."},
        "jds":[
            {"title":"Software Engineering Intern (Go/Python)","quota":3,"target_department":"Computer Science / Software Engineering",
             "location":"Yaba, Lagos","required_skills":["go","python","postgresql","redis","docker","rest api","git","microservices"],
             "raw_text":"Build distributed backend services in Go and Python. Quota: 3."},
        ]
    },
    {
        "company": {"name":"CyberVergent","email":"careers@cybervergent.com",
                    "industry":"Cybersecurity","location":"Victoria Island, Lagos","state":"Lagos",
                    "website":"https://cybervergent.com",
                    "description":"Enterprise cybersecurity services across Africa."},
        "jds":[
            {"title":"Cybersecurity Analyst Intern","quota":3,"target_department":"Computer Science / Cyber Security",
             "location":"Victoria Island, Lagos","required_skills":["cybersecurity","networking","linux","python","penetration testing","wireshark","ethical hacking"],
             "raw_text":"Vulnerability assessments and SIEM monitoring. Quota: 3."},
        ]
    },
    {
        "company": {"name":"Jumia Nigeria","email":"tech-intern@jumia.com.ng",
                    "industry":"E-Commerce","location":"Ikeja, Lagos","state":"Lagos",
                    "website":"https://jumia.com.ng",
                    "description":"Africa's leading e-commerce marketplace."},
        "jds":[
            {"title":"Backend Engineering Intern","quota":4,"target_department":"Computer Science",
             "location":"Ikeja, Lagos","required_skills":["python","java","go","rest api","mongodb","postgresql","docker","git"],
             "raw_text":"Build scalable microservices for marketplace. Quota: 4."},
        ]
    },

    # ══════════════════════════════════════
    # ABUJA
    # ══════════════════════════════════════
    {
        "company": {"name":"Microsystems (Abuja)","email":"hr@microsystems.ng",
                    "industry":"IT Services","location":"Wuse 2, Abuja","state":"Abuja",
                    "website":"https://microsystems.ng",
                    "description":"Leading ICT solutions and managed services company in FCT."},
        "jds":[
            {"title":"Software Developer Intern","quota":3,"target_department":"Computer Science / Software Engineering",
             "location":"Wuse 2, Abuja","required_skills":["python","javascript","react","sql","git","rest api"],
             "raw_text":"Build and maintain client-facing web applications. Quota: 3."},
            {"title":"IT Support / Networking Intern","quota":2,"target_department":"Computer Engineering / IT",
             "location":"Wuse 2, Abuja","required_skills":["networking","linux","cisco","windows server","sql","bash"],
             "raw_text":"Support network infrastructure and end-user systems. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Accelerex Network","email":"internship@accelerex.ng",
                    "industry":"Fintech","location":"Central Business District, Abuja","state":"Abuja",
                    "website":"https://accelerex.ng",
                    "description":"Electronic payment infrastructure serving banks across Nigeria."},
        "jds":[
            {"title":"Backend API Intern","quota":2,"target_department":"Computer Science / Software Engineering",
             "location":"Central Business District, Abuja","required_skills":["java","spring boot","rest api","postgresql","git","agile"],
             "raw_text":"Develop payment processing APIs in Java/Spring Boot. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Galaxy Backbone","email":"it-intern@galaxybackbone.com.ng",
                    "industry":"Cloud / Government ICT","location":"Garki, Abuja","state":"Abuja",
                    "website":"https://galaxybackbone.com.ng",
                    "description":"Government-owned ICT infrastructure and cloud services provider."},
        "jds":[
            {"title":"Cloud Infrastructure Intern","quota":4,"target_department":"Computer Engineering / IT",
             "location":"Garki, Abuja","required_skills":["linux","networking","aws","docker","python","bash","cisco","sql"],
             "raw_text":"Manage government cloud infrastructure and data centres. Quota: 4."},
            {"title":"Cybersecurity Intern","quota":2,"target_department":"Computer Science / Cyber Security",
             "location":"Garki, Abuja","required_skills":["cybersecurity","networking","linux","python","wireshark","penetration testing"],
             "raw_text":"Monitor and secure government network assets. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Softcom Limited","email":"hr@softcom.ng",
                    "industry":"Software Development","location":"Maitama, Abuja","state":"Abuja",
                    "website":"https://softcom.ng",
                    "description":"Building digital products for African enterprises."},
        "jds":[
            {"title":"Frontend Engineering Intern","quota":2,"target_department":"Computer Science / IT",
             "location":"Maitama, Abuja","required_skills":["javascript","react","typescript","css","git","rest api","nextjs"],
             "raw_text":"Build user interfaces in React/Next.js. Quota: 2."},
        ]
    },

    # ══════════════════════════════════════
    # IBADAN
    # ══════════════════════════════════════
    {
        "company": {"name":"Bluechip Technologies","email":"internship@bluechip.ng",
                    "industry":"Fintech / Data","location":"Ring Road, Ibadan","state":"Ibadan",
                    "website":"https://bluechip.ng",
                    "description":"AI-driven financial data analytics company serving African banks."},
        "jds":[
            {"title":"Data Science Intern","quota":3,"target_department":"Computer Science / Data Science",
             "location":"Ring Road, Ibadan","required_skills":["python","machine learning","pandas","scikit-learn","sql","numpy","data analysis"],
             "raw_text":"Build predictive models for financial data. Quota: 3."},
            {"title":"Backend Python Intern","quota":2,"target_department":"Computer Science / Software Engineering",
             "location":"Ring Road, Ibadan","required_skills":["python","django","flask","postgresql","git","rest api"],
             "raw_text":"Develop APIs for analytics platform. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Cowrywise","email":"talent@cowrywise.com",
                    "industry":"Fintech","location":"UI Road, Ibadan","state":"Ibadan",
                    "website":"https://cowrywise.com",
                    "description":"Investment and savings platform for Nigerians."},
        "jds":[
            {"title":"Mobile Development Intern","quota":2,"target_department":"Computer Science / Software Engineering",
             "location":"UI Road, Ibadan","required_skills":["flutter","dart","firebase","rest api","git","android","ios"],
             "raw_text":"Build features on Flutter investment app. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Terragon Group","email":"intern@terragon.com.ng",
                    "industry":"Marketing Tech / Data","location":"Bodija, Ibadan","state":"Ibadan",
                    "website":"https://terragon.com.ng",
                    "description":"Africa's leading data and marketing technology company."},
        "jds":[
            {"title":"Data Engineering Intern","quota":2,"target_department":"Computer Science / IT",
             "location":"Bodija, Ibadan","required_skills":["python","sql","pandas","docker","git","data analysis","postgresql"],
             "raw_text":"Build data pipelines for marketing analytics. Quota: 2."},
        ]
    },

    # ══════════════════════════════════════
    # CALABAR
    # ══════════════════════════════════════
    {
        "company": {"name":"Agilizor Systems","email":"hr@agilizor.com",
                    "industry":"Software Development","location":"State Housing, Calabar","state":"Calabar",
                    "website":"https://agilizor.com",
                    "description":"Enterprise software solutions across South-South Nigeria."},
        "jds":[
            {"title":"Full Stack Developer Intern","quota":2,"target_department":"Computer Science / Software Engineering",
             "location":"State Housing, Calabar","required_skills":["javascript","react","nodejs","postgresql","git","rest api","css"],
             "raw_text":"Build web applications using React and Node.js. Quota: 2."},
        ]
    },
    {
        "company": {"name":"CRS ICT Agency","email":"ict@crsstate.gov.ng",
                    "industry":"Government ICT","location":"MCC Road, Calabar","state":"Calabar",
                    "website":"https://crsstate.gov.ng",
                    "description":"Cross River State ICT development and digital infrastructure agency."},
        "jds":[
            {"title":"Software Developer Intern","quota":3,"target_department":"Computer Science / IT",
             "location":"MCC Road, Calabar","required_skills":["python","javascript","sql","git","linux","rest api","networking"],
             "raw_text":"Build and support government digital platforms. Quota: 3."},
            {"title":"IT Infrastructure Intern","quota":2,"target_department":"Computer Engineering",
             "location":"MCC Road, Calabar","required_skills":["networking","linux","cisco","windows server","bash","sql"],
             "raw_text":"Maintain state government IT infrastructure. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Calabar Innovation Hub","email":"info@calabarhub.ng",
                    "industry":"Tech Startup / Innovation","location":"Efio-Ette, Calabar","state":"Calabar",
                    "website":"https://calabarhub.ng",
                    "description":"Cross River's leading technology innovation and incubation centre."},
        "jds":[
            {"title":"Frontend Intern","quota":2,"target_department":"Computer Science",
             "location":"Efio-Ette, Calabar","required_skills":["javascript","react","css","git","html","rest api"],
             "raw_text":"Build UIs for startup products. Quota: 2."},
        ]
    },

    # ══════════════════════════════════════
    # KWARA
    # ══════════════════════════════════════
    {
        "company": {"name":"Sokoloan Finance","email":"hr@sokoloan.com",
                    "industry":"Fintech","location":"GRA, Ilorin, Kwara","state":"Kwara",
                    "website":"https://sokoloan.com",
                    "description":"Digital lending and microfinance platform in North-Central Nigeria."},
        "jds":[
            {"title":"Backend Developer Intern","quota":2,"target_department":"Computer Science / Software Engineering",
             "location":"GRA, Ilorin, Kwara","required_skills":["python","flask","fastapi","postgresql","git","rest api","redis"],
             "raw_text":"Build loan processing APIs using Python/FastAPI. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Kwara State ICT Agency (KWICTDA)","email":"internship@kwictda.gov.ng",
                    "industry":"Government ICT","location":"Ilorin, Kwara","state":"Kwara",
                    "website":"https://kwictda.gov.ng",
                    "description":"Kwara State ICT and digital transformation agency."},
        "jds":[
            {"title":"IT Systems Intern","quota":4,"target_department":"Computer Science / Computer Engineering",
             "location":"Ilorin, Kwara","required_skills":["python","sql","linux","networking","git","windows server"],
             "raw_text":"Support digital transformation projects across state MDAs. Quota: 4."},
            {"title":"Data Analyst Intern","quota":2,"target_department":"Computer Science / IT",
             "location":"Ilorin, Kwara","required_skills":["python","pandas","sql","excel","data analysis","tableau"],
             "raw_text":"Analyse government service delivery data. Quota: 2."},
        ]
    },
    {
        "company": {"name":"Harmony Innovation Lab","email":"hello@harmonylab.ng",
                    "industry":"Software Development","location":"University Road, Ilorin, Kwara","state":"Kwara",
                    "website":"https://harmonylab.ng",
                    "description":"Product studio building SaaS tools for Nigerian SMEs."},
        "jds":[
            {"title":"Full Stack Intern","quota":2,"target_department":"Computer Science",
             "location":"University Road, Ilorin, Kwara","required_skills":["javascript","react","nodejs","postgresql","git","rest api"],
             "raw_text":"Build SaaS product features in React and Node.js. Quota: 2."},
        ]
    },
]


def seed_companies_extended():
    """Insert pre-registered companies with User accounts and default passwords."""
    init_db()
    _ensure_remaining_quota_col()

    db = SessionLocal()
    added_c = added_j = 0
    credentials = []

    try:
        for entry in COMPANIES:
            c_data = entry["company"]
            default_pw = _default_password(c_data["name"])

            # ── User account ──────────────────────────────────────────────────
            user = db.query(User).filter_by(email=c_data["email"]).first()
            if not user:
                user = User(email=c_data["email"], role="admin")
                user.set_password(default_pw)
                db.add(user)
                db.flush()

            # ── Company record ────────────────────────────────────────────────
            company = db.query(Company).filter_by(name=c_data["name"]).first()
            if company:
                # Link user if not already linked
                if company.user_id is None:
                    company.user_id = user.id
                print(f"[SKIP] {c_data['name']} already exists")
            else:
                company = Company(
                    user_id=user.id,
                    name=c_data["name"],
                    email=c_data["email"],
                    industry=c_data["industry"],
                    location=c_data["location"],
                    state=c_data["state"],
                    website=c_data["website"],
                    description=c_data["description"],
                    verified=True,
                )
                db.add(company)
                db.flush()
                added_c += 1
                credentials.append({
                    "company":  c_data["name"],
                    "email":    c_data["email"],
                    "password": default_pw,
                    "state":    c_data["state"],
                })
                print(f"[OK] {c_data['name']} ({c_data['state']})  pw={default_pw}")

            # ── Job descriptions ──────────────────────────────────────────────
            for jd_data in entry["jds"]:
                ex = db.query(JobDescription).filter_by(
                    company_id=company.id, title=jd_data["title"]).first()
                if ex:
                    continue
                jd = JobDescription(
                    company_id=company.id,
                    title=jd_data["title"],
                    raw_text=jd_data["raw_text"],
                    target_department=jd_data["target_department"],
                    location=jd_data["location"],
                    quota=jd_data["quota"],
                    remaining_quota=jd_data["quota"],   # starts full
                )
                jd.set_required_skills(jd_data["required_skills"])
                db.add(jd)
                added_j += 1

        db.commit()

        # ── Print credentials table ───────────────────────────────────────────
        if credentials:
            print("\n" + "═" * 72)
            print("  DEFAULT ADMIN CREDENTIALS (change on first login)")
            print("═" * 72)
            for c in credentials:
                print(f"  {c['company']:<30} {c['email']:<40}")
                print(f"  {'':30} Password: {c['password']}")
                print()
            print("═" * 72)

        print(f"\n✅ {added_c} new companies · {added_j} job descriptions seeded.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


def _ensure_remaining_quota_col():
    """
    Add remaining_quota column to job_descriptions if it doesn't exist yet
    (safe to call multiple times — uses IF NOT EXISTS logic).
    """
    with engine.connect() as conn:
        try:
            # SQLite
            conn.execute(text(
                "ALTER TABLE job_descriptions ADD COLUMN remaining_quota INTEGER"
            ))
            conn.execute(text(
                "UPDATE job_descriptions SET remaining_quota = quota "
                "WHERE remaining_quota IS NULL"
            ))
            conn.commit()
            print("[DB] Added remaining_quota column.")
        except Exception:
            # Column already exists — fine
            pass


def reduce_quotas_after_placement(batch_id: int):
    """
    Call this after a placement run to decrement each JD's remaining_quota
    by the number of students placed into it in that batch.

    Usage:
        from seed_companies_extended import reduce_quotas_after_placement
        reduce_quotas_after_placement(batch_id)
    """
    _ensure_remaining_quota_col()
    db = SessionLocal()
    try:
        placements = db.query(Placement).filter_by(batch_id=batch_id).all()

        # Count placements per JD
        from collections import Counter
        counts = Counter(p.job_description_id for p in placements)

        updated = 0
        for jd_id, placed_count in counts.items():
            jd = db.query(JobDescription).filter_by(id=jd_id).first()
            if jd:
                current = jd.remaining_quota if jd.remaining_quota is not None else jd.quota
                jd.remaining_quota = max(0, current - placed_count)
                updated += 1

        db.commit()
        print(f"[QUOTA] Reduced remaining_quota for {updated} JDs after batch {batch_id}.")
    except Exception as e:
        db.rollback()
        print(f"[QUOTA ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_companies_extended()

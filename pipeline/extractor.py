"""
pipeline/extractor.py  —  Feature extraction using spaCy NER + PhraseMatcher
Extracts: skills, location, department from raw CV / JD text.
"""

import spacy
from spacy.matcher import PhraseMatcher
import re

# ─────────────────────────────────────────────
# Master skill taxonomy (Nigerian CS context)
# ─────────────────────────────────────────────
SKILLS_TAXONOMY = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "kotlin", "swift", "php", "ruby", "scala", "r", "matlab",

    # Web frameworks / libraries
    "django", "flask", "fastapi", "react", "vue", "angular", "nextjs",
    "nodejs", "express", "spring boot", "laravel",

    # Databases
    "mysql", "postgresql", "mongodb", "sqlite", "redis", "firebase",
    "oracle", "sql server", "cassandra",

    # DevOps / Cloud
    "docker", "kubernetes", "aws", "gcp", "azure", "linux", "git",
    "ci/cd", "jenkins", "terraform", "nginx",

    # Data / ML
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "pandas", "numpy", "data analysis", "tableau", "power bi", "excel",
    "natural language processing", "nlp", "computer vision",

    # Mobile
    "android", "ios", "flutter", "react native",

    # Networking / Security
    "networking", "cybersecurity", "penetration testing", "ethical hacking",
    "cisco", "wireshark",

    # Soft / general
    "agile", "scrum", "rest api", "graphql", "microservices",
    "object oriented programming", "oop", "data structures", "algorithms",
    "backend development", "frontend development", "full stack",
    "software engineering", "system design", "technical writing",
}

# Nigerian SW locations
NIGERIA_SW_LOCATIONS = {
    "lagos", "ikeja", "victoria island", "lekki", "ajah", "yaba", "surulere",
    "ikorodu", "apapa", "oshodi", "mushin", "isale-eko",
    "ibadan", "abeokuta", "akure", "ilorin", "osogbo",
    "ogun", "ondo", "ekiti", "oyo", "kwara",
}

# CS department synonyms
CS_DEPARTMENTS = {
    "computer science", "computer engineering", "software engineering",
    "information technology", "it", "cs", "csc", "information systems",
    "electrical electronics", "electrical/electronics", "systems engineering",
    "cyber security", "data science",
}


class FeatureExtractor:
    """
    Extracts structured features from free-form CV / JD text.
    Uses:
      - spaCy NER for LOCATION entities
      - PhraseMatcher for skills (case-insensitive)
      - Regex + phrase matching for department
    """

    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError(
                "spaCy model not found. Run: python -m spacy download en_core_web_sm"
            )

        self._build_matchers()

    def _build_matchers(self):
        # Skills matcher
        self.skill_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        skill_patterns = [self.nlp.make_doc(s) for s in SKILLS_TAXONOMY]
        self.skill_matcher.add("SKILL", skill_patterns)

        # Location matcher (supplement spaCy NER)
        self.loc_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        loc_patterns = [self.nlp.make_doc(l) for l in NIGERIA_SW_LOCATIONS]
        self.loc_matcher.add("NGA_LOCATION", loc_patterns)

        # Department matcher
        self.dept_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        dept_patterns = [self.nlp.make_doc(d) for d in CS_DEPARTMENTS]
        self.dept_matcher.add("DEPARTMENT", dept_patterns)

    # ── Public API ────────────────────────────

    def extract_from_cv(self, text: str) -> dict:
        """
        Extract skills, location, department from a student's CV text.
        Returns dict with keys: skills (list), location (str), department (str).
        """
        return self._extract(text, mode="cv")

    def extract_from_jd(self, text: str) -> dict:
        """
        Extract required skills, location, quota from a job description.
        Returns dict with keys: skills (list), location (str), department (str), quota (int).
        """
        result = self._extract(text, mode="jd")
        result["quota"] = self._extract_quota(text)
        return result

    # ── Internal ──────────────────────────────

    def _extract(self, text: str, mode: str) -> dict:
        clean = self._clean_text(text)
        doc   = self.nlp(clean)

        skills     = self._get_skills(doc)
        location   = self._get_location(doc)
        department = self._get_department(doc)

        return {
            "skills":     skills,
            "location":   location,
            "department": department,
        }

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\.,/\-+#]", " ", text)
        return text.strip()

    def _get_skills(self, doc) -> list:
        matches = self.skill_matcher(doc)
        found = set()
        for _, start, end in matches:
            skill = doc[start:end].text.lower()
            found.add(skill)
        return sorted(found)

    def _get_location(self, doc) -> str:
        # 1. Try PhraseMatcher for Nigerian locations
        matches = self.loc_matcher(doc)
        if matches:
            _, start, end = matches[0]
            return doc[start:end].text.title()

        # 2. Fall back to spaCy NER GPE/LOC entities
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                return ent.text.title()

        return "Lagos"  # sensible default

    def _get_department(self, doc) -> str:
        matches = self.dept_matcher(doc)
        if matches:
            _, start, end = matches[0]
            return doc[start:end].text.title()
        return "Computer Science"

    def _extract_quota(self, text: str) -> int:
        """
        Parse lines like 'Vacancy: 3', 'Slots: 2', 'Number of students: 5'.
        Defaults to 1 if nothing is found.
        """
        patterns = [
            r"(?:quota|vacancy|vacancies|slots?|positions?|students?)[:\s]+(\d+)",
            r"(\d+)\s+(?:slot|position|student|vacancy)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return max(1, int(m.group(1)))
        return 1


# ── Module-level singleton ────────────────────
_extractor: FeatureExtractor | None = None

def get_extractor() -> FeatureExtractor:
    global _extractor
    if _extractor is None:
        _extractor = FeatureExtractor()
    return _extractor

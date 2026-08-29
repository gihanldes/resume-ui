"""Word lists used by the deterministic review rules.

Kept as plain Python so they are importable without I/O and easy to extend.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Strong action verbs, grouped so feedback can suggest a relevant alternative.
# --------------------------------------------------------------------------- #
ACTION_VERBS: dict[str, frozenset[str]] = {
    "leadership": frozenset(
        """led directed managed supervised coordinated orchestrated chaired headed
        mentored coached guided oversaw spearheaded championed mobilised mobilized
        delegated founded established chartered""".split()
    ),
    "achievement": frozenset(
        """achieved delivered exceeded surpassed outperformed won secured attained
        completed shipped launched released landed closed captured""".split()
    ),
    "improvement": frozenset(
        """improved increased reduced decreased optimised optimized streamlined
        accelerated boosted enhanced strengthened doubled tripled cut eliminated
        minimised minimized maximised maximized upgraded refactored modernised
        modernized consolidated simplified""".split()
    ),
    "creation": frozenset(
        """built created designed developed engineered architected implemented
        prototyped authored produced formulated devised introduced pioneered
        constructed programmed composed drafted""".split()
    ),
    "analysis": frozenset(
        """analysed analyzed evaluated assessed researched investigated diagnosed
        audited measured modelled modeled forecasted quantified benchmarked
        identified validated tested surveyed""".split()
    ),
    "collaboration": frozenset(
        """collaborated partnered negotiated facilitated liaised presented advised
        consulted influenced aligned briefed persuaded represented""".split()
    ),
    "operations": frozenset(
        """automated migrated deployed maintained scaled integrated configured
        administered monitored resolved troubleshot standardised standardized
        documented trained onboarded""".split()
    ),
}

ALL_ACTION_VERBS: frozenset[str] = frozenset().union(*ACTION_VERBS.values())

# --------------------------------------------------------------------------- #
# Openers that describe duties rather than results.
# --------------------------------------------------------------------------- #
WEAK_OPENERS: frozenset[str] = frozenset(
    """responsible worked helped assisted participated involved tasked duties
    handled dealt performed did made used utilised utilized attended supported
    contributed""".split()
)

# Phrases that add length without information.
FILLER_PHRASES: tuple[str, ...] = (
    "responsible for",
    "duties included",
    "in charge of",
    "tasked with",
    "worked on",
    "helped with",
    "assisted with",
    "participated in",
    "involved in",
    "various tasks",
    "day to day",
    "day-to-day",
    "as needed",
    "etc.",
    "and more",
    "among others",
)

# Self-descriptions that assert instead of evidencing.
CLICHE_PHRASES: tuple[str, ...] = (
    "team player",
    "hard worker",
    "hard working",
    "hardworking",
    "self-starter",
    "self starter",
    "go-getter",
    "detail oriented",
    "detail-oriented",
    "results driven",
    "results-driven",
    "results oriented",
    "results-oriented",
    "think outside the box",
    "thinks outside the box",
    "outside the box",
    "proven track record",
    "dynamic professional",
    "excellent communication skills",
    "strong work ethic",
    "highly motivated",
    "goes above and beyond",
    "wear many hats",
    "synergy",
    "ninja",
    "rockstar",
    "guru",
)

FIRST_PERSON_PRONOUNS: frozenset[str] = frozenset(
    {"i", "me", "my", "mine", "myself", "we", "our", "ours", "us"}
)

# --------------------------------------------------------------------------- #
# Section vocabulary. Keys are canonical names; values are heading synonyms.
# --------------------------------------------------------------------------- #
SECTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "summary": (
        "summary",
        "professional summary",
        "career summary",
        "executive summary",
        "profile",
        "professional profile",
        "about",
        "about me",
        "objective",
        "career objective",
        "overview",
    ),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "work history",
        "career history",
        "relevant experience",
        "industry experience",
    ),
    "education": (
        "education",
        "academic background",
        "academics",
        "qualifications",
        "academic qualifications",
        "educational background",
    ),
    "skills": (
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "core competencies",
        "competencies",
        "areas of expertise",
        "technologies",
        "technical proficiencies",
        "tech stack",
    ),
    "projects": ("projects", "personal projects", "side projects", "selected projects", "portfolio"),
    "certifications": (
        "certifications",
        "certificates",
        "licenses",
        "licences",
        "licenses and certifications",
        "professional development",
        "courses",
        "training",
    ),
    "awards": ("awards", "honors", "honours", "achievements", "accomplishments", "recognition"),
    "publications": ("publications", "papers", "research", "talks", "conference talks", "speaking"),
    "volunteer": ("volunteer", "volunteering", "volunteer experience", "community involvement"),
    "languages": ("languages", "language skills", "spoken languages"),
    "interests": ("interests", "hobbies", "hobbies and interests", "personal interests"),
    "references": ("references", "referees"),
}

CANONICAL_SECTIONS: tuple[str, ...] = tuple(SECTION_SYNONYMS)

# Sections a reviewer expects to find on essentially any resume.
REQUIRED_SECTIONS: tuple[str, ...] = ("experience", "education", "skills")
RECOMMENDED_SECTIONS: tuple[str, ...] = ("summary",)
# Sections that consume space without helping in most markets.
LOW_VALUE_SECTIONS: tuple[str, ...] = ("references", "interests")

# --------------------------------------------------------------------------- #
# Skills taxonomy — used to recognise technical keywords in a job description
# even when the resume phrases them differently.
# --------------------------------------------------------------------------- #
SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "javascript": ("js", "ecmascript", "es6"),
    "typescript": ("ts",),
    "python": ("py",),
    "postgresql": ("postgres", "psql"),
    "kubernetes": ("k8s",),
    "amazon web services": ("aws",),
    "google cloud platform": ("gcp", "google cloud"),
    "microsoft azure": ("azure",),
    "continuous integration": ("ci", "ci/cd", "cicd"),
    "machine learning": ("ml",),
    "artificial intelligence": ("ai",),
    "natural language processing": ("nlp",),
    "user interface": ("ui",),
    "user experience": ("ux",),
    "representational state transfer": ("rest", "restful", "rest api"),
    "structured query language": ("sql",),
    "react": ("react.js", "reactjs"),
    "node.js": ("node", "nodejs"),
    "vue.js": ("vue", "vuejs"),
    "angular": ("angular.js", "angularjs"),
    ".net": ("dotnet", "asp.net"),
    "c#": ("csharp",),
    "c++": ("cpp",),
    "objective-c": ("objc",),
    "infrastructure as code": ("iac", "terraform"),
    "search engine optimization": ("seo",),
    "customer relationship management": ("crm",),
    "key performance indicator": ("kpi", "kpis"),
    "business intelligence": ("bi",),
    "extract transform load": ("etl",),
    "quality assurance": ("qa",),
    "test driven development": ("tdd",),
    "agile": ("scrum", "kanban", "sprint"),
}

# Reverse index: alias -> canonical
ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical for canonical, aliases in SKILL_ALIASES.items() for alias in aliases
}

# --------------------------------------------------------------------------- #
# Stopwords for keyword extraction. Deliberately broad: job descriptions are
# full of boilerplate that must not be treated as a required skill.
# --------------------------------------------------------------------------- #
STOPWORDS: frozenset[str] = frozenset(
    """a about above across after again against all almost alone along already also
    although always am among an and another any anybody anyone anything anywhere are
    area around as at away back be became because become been before began behind
    being below beside besides best better between beyond both but by came can cannot
    could did do does doing done down during each either else enough etc even ever
    every everybody everyone everything except far few find first for from further
    get give go going good got great had has have having he her here hers herself him
    himself his how however i if in include including indeed instead into is it its
    itself just keep kept know known last later least less let like likely long look
    made make many may me meanwhile might more moreover most much must my myself near
    need neither never nevertheless new next no nobody none nor not nothing now
    nowhere of off often on once one only onto or other others otherwise ought our
    ours ourselves out over own per perhaps please put quite rather really said same
    say says see seem seen several shall she should since so some somebody someone
    something sometimes somewhere still such take taken than that the their theirs
    them themselves then there therefore these they thing things think this those
    though through throughout thus to together too toward towards under until up upon
    us use used using usually very via want was way we well went were what whatever
    when whenever where whereas whether which while who whoever whom whose why will
    with within without would yet you your yours yourself yourselves
    ability able across additional applicant apply candidate candidates company
    description employer environment equal experience join looking opportunity
    position preferred qualifications required requirements responsibilities role
    salary skills strong team teams work working years plus etc ideal successful
    excellent proven demonstrated ensure ensuring help helping support supporting
    across level senior junior mid full time part benefits offer offers we're you'll
    who what where when how our their its""".split()
)

# Words that look like skills but are almost always noise in a JD.
KEYWORD_BLOCKLIST: frozenset[str] = frozenset(
    """resume cv cover letter email phone address linkedin github portfolio
    reference references contact recruiter hiring manager interview offer
    remote hybrid onsite office location city state country visa sponsorship
    bachelor bachelors master masters degree diploma phd""".split()
)

from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Company

# ── Segment → supply chain (for companies that have energy_segment set) ────────
_SEGMENT_MAP: dict[str, str] = {
    "Integrated Gas":              "Integrated",
    "Onshore":                     "Upstream",
    "Offshore":                    "Upstream",
    "Combustion Energy":           "Downstream",
    "Midstream Infrastructure":    "Midstream",
    "Petrochemicals":              "Petrochemicals",
    "Chemicals":                   "Petrochemicals",
    "Refined Fuels":               "Downstream",
    "Specialty Chemicals":         "Petrochemicals",
    "Fuel Transport":              "Midstream",
    "Bulk Minerals":               "Upstream",
    "Agriculture Plants":          "Downstream",
    "Resource Infrastructure":     "Midstream",
    "Metals":                      "Upstream",
    "Low Carbon Hydrogen":         "Upstream",
    "Renewable Energy":            "Upstream",
    "Energy Storage":              "Midstream",
    "Nuclear SMR":                 "Upstream",
    "Power to X":                  "Services",
    "Low Carbon Fuels":            "Downstream",
    "Direct Air Capture":          "Services",
    "Ammonia/Methanol":            "Petrochemicals",
    "Plastics Recovery":           "Services",
    "Energy Transition Materials": "Services",
    "Battery Materials":           "Services",
    "Water Recycling":             "Services",
}

# ── Ordered name-substring rules ─────────────────────────────────────────────
# Checked in order; first match wins. All strings are lowercase.
_NAME_RULES: list[tuple[str, list[str]]] = [
    # Integrated majors & national oil companies
    ("Integrated", [
        "exxon", "shell", "totalenergies", "total energies", "chevron",
        "equinor", "petrobras", "sinopec", "petrochina", "saudi aramco",
        "lukoil", "gazprom", "repsol", "suncor", "cepsa",
        "rosneft", "cnooc", "taqa", "adnoc",
        "ongc", "oil & natural gas corp", "ioc ltd",
        "bharat petroleum", "hindustan petroleum",
        "pertamina", "pemex", "sonatrach",
        "omv ag", "omv group",
        "ptt public", "ptt group", "ptt pcl",
        "conocophillips",
        "cenovus",
        "imperial oil",
        "husky energy",
        "inpex",
        "woodside energy",   # Australian integrated
        "santos ltd",
        "oil search",
    ]),

    # Petrochemicals (before generic "chemical" fallback)
    ("Petrochemicals", [
        "petrochemical", "polymer", "polypropylene", "polyethylene",
        "fertilizer", "ammonia ", " ammonia", "methanol",
        "lyondellbasell", "lyondell",
        "basf", "dow chemical", "dow inc",
        "sabic", "eastman chemical", "celanese", "huntsman",
        "trinseo", "ineos", "borealis", "braskem", "indorama",
        "evonik", "lanxess", "arkema", "tosoh",
        "asahi kasei", "sumitomo chemical", "mitsui chemicals",
        "toray", "covestro", "solvay", "clariant",
        "linde plc", "air products", "air liquide", "praxair",
    ]),

    # Midstream — pipelines, LNG, storage, gathering
    ("Midstream", [
        "pipeline", "pipelines", "midstream", "regasif", "liquefaction",
        "gathering system", "transmission co",
        "enbridge", "tc energy", "tc pipelines", "transcanada",
        "kinder morgan", "williams companies", "williams partners",
        "oneok", "energy transfer", "targa resources",
        "enterprise products", "mplx",
        "magellan midstream", "plains all american",
        "cheniere energy", "crestwood midstream",
        "boardwalk pipeline", "pembina pipeline",
        "keyera", "inter pipeline",
        "dcp midstream", "holly midstream", "summit midstream",
        "new fortress energy", "sempra lng",
        "flex lng", "golar lng",
    ]),

    # Oilfield services & drilling
    ("Services", [
        "schlumberger", " slb", "halliburton", "baker hughes",
        "weatherford", "technip", "saipem", "subsea 7",
        "oceaneering", "core lab", "core laboratories",
        "championx", "aspentech", "forum energy", "oil states",
        "dril-quip", "frank's international",
        "archrock", "exterran",
        "cgg ", "pgs asa", "tgs ",
        "valaris", "transocean", "diamond offshore",
        "ensco", "rowan companies", "paragon offshore",
        "helmerich", "patterson-uti", "nabors",
        "tetra technologies", "newpark resources",
        "borr drilling", "noble corporation",
        "geophysic", "seismic survey",
    ]),

    # Downstream — refining, retail fuel, marketing
    ("Downstream", [
        "refining", "refinery", "refineries",
        "phillips 66", "valero energy", "valero ",
        "marathon petroleum", "motiva enterprises",
        "pbf energy", "par pacific", "calumet specialty",
        "hf sinclair", "holly frontier", "delek group",
        "neste oil", "neste corp",
        "indian oil", "hindustan petroleum",
        "retail fuel", "fuel station", "petrol station",
        "tesoro", "sunoco lp", "global partners lp",
    ]),

    # Named E&P companies not covered by keywords above
    ("Upstream", [
        "exploration", " e&p", "e&p ",
        "eog resources", "diamondback energy",
        "pioneer natural resources", "coterra",
        "devon energy", "continental resources",
        "callon petroleum", "oasis petroleum",
        "whiting petroleum", "sm energy", "cimarex",
        "centennial resource", "bonanza creek",
        "canadian natural resources", "arc resources",
        "tamarack valley", "whitecap resources",
        "crescent point", "parex resources",
        "ovintiv", "tourmaline", "peyto",
        "vermilion energy", "baytex",
        "novatek",
        "eqt corporation",
        "southwestern energy",
        "range resources",
        "antero resources",
        "comstock resources",
        "chesapeake energy",
        "occidental petroleum",
        "hess corp", "hess corporation",
        "concho resources",
        "harbour energy",
        "tullow oil",
        "energean",
        "ithaca energy",
        "seplat energy",
        # additional E&P companies
        "apache corporation", "apa corporation",
        "africa oil", "amplify energy",
        "advantage energy", "birchcliff energy",
        "bluenord", "canacol energy",
        "capricorn energy", "cardinal energy",
        "carnarvon energy", "caspian sunrise",
        "chord energy", "coelacanth energy",
        "cooper energy", "crescent energy",
        "dno asa", "dana gas",
        "battalion oil", "bkv corporation",
        "black stone minerals",
        "afentra",
        "calvalley petroleum",
        "shield energy", "el nino ventures",
        "solaris resources", "sable offshore",
        "vaalco energy", "ring energy",
        "gran tierra", "vista energy",
        "pan orient energy", "madalena energy",
        "cypress development", "perpetua resources",
        "genie energy", "gastar exploration",
        "high peak energy", "solaris oilfield",
    ]),

    # Additional midstream (gas utilities & distribution)
    ("Midstream", [
        "altagas", "atco gas", "chesapeake utilities",
        "china gas", "adani total gas", "adani gas",
        "indraprastha gas", "mahanagar gas",
        "gas distribution", "natural gas distribution",
        "gas utility", "gas network",
        "equitable gas", "national fuel gas",
        "uecu", "southern union",
        "clean energy fuels",  # CNG fueling stations
    ]),

    # Additional downstream
    ("Downstream", [
        "ampol", "castrol", "crossamerica",
        "dcc plc", "dcc energy",
        "aldrees petroleum",
        "cbl international",
        "delek us", "delek logistics",
        "sprague resources",
        "world fuel services",
        "geo group",
    ]),
]

# ── Generic keyword fallbacks (no explicit company match, no segment data) ────
_GENERIC_PETROCHEM  = ["chemical", "chemicals", "polymer", "plastic ",
                        "plastics", "rubber ", "resin ", "fibre", "fiber "]
_GENERIC_MIDSTREAM  = ["storage terminal", "distribution grid",
                        "fuel transport", "gas transmission", " lng "]
_GENERIC_SERVICES   = [" services", "service co", "service ltd",
                        "oilfield", "well services", "drilling co",
                        "drilling ltd", "equipment co", "equipment ltd",
                        "technology solutions", "energy solutions",
                        "engineering services"]
_GENERIC_DOWNSTREAM = ["petroleum products", "oil marketing",
                        "fuel marketing", "fuel distribution", "downstream"]
_GENERIC_UPSTREAM   = ["petroleum corp", "petroleum ltd", "petroleum plc",
                        "petroleum inc", "oil corp", "oil ltd",
                        " resources ltd", " resources inc", " resources plc",
                        "natural gas corp", "coal ", " mining",
                        "mining co", "mining ltd", "mining plc",
                        "oil & gas", "oil and gas", "upstream petroleum"]


def _classify(c: Company) -> str:
    name = c.name.lower()

    # 1. Named-company / keyword rules
    for position, keywords in _NAME_RULES:
        if any(kw in name for kw in keywords):
            return position

    # BP — 2-char name needs word-boundary matching
    padded = f" {name} "
    if " bp " in padded or name in ("bp", "bp plc", "bp p.l.c"):
        return "Integrated"

    # ENI — 3-char name; safe to match as substring (not in other words)
    if " eni " in padded or name in ("eni", "eni plc"):
        return "Integrated"

    # 2. Segment mapping
    if c.energy_segment:
        seg = c.energy_segment.value if hasattr(c.energy_segment, "value") else str(c.energy_segment)
        if seg in _SEGMENT_MAP:
            return _SEGMENT_MAP[seg]

    # 3. Existing value_chain_position as structured fallback
    if c.value_chain_position:
        return c.value_chain_position.value if hasattr(c.value_chain_position, "value") else str(c.value_chain_position)

    # 4. Generic keyword fallbacks
    for kw in _GENERIC_PETROCHEM:
        if kw in name:
            return "Petrochemicals"
    for kw in _GENERIC_MIDSTREAM:
        if kw in name:
            return "Midstream"
    for kw in _GENERIC_SERVICES:
        if kw in name:
            return "Services"
    for kw in _GENERIC_DOWNSTREAM:
        if kw in name:
            return "Downstream"
    for kw in _GENERIC_UPSTREAM:
        if kw in name:
            return "Upstream"

    # 5. Energy-category hint (last resort before default)
    if c.energy_category:
        cat = c.energy_category.value if hasattr(c.energy_category, "value") else str(c.energy_category)
        if cat == "Chemicals":
            return "Petrochemicals"
        if cat in ("Energy", "Resources"):
            return "Upstream"

    # 6. Generic upstream signals — use padded name for word-boundary matching
    upstream_generic = [
        "petroleum", " oil ", " oil,", "natural gas",
        " resources", "energy corp", "energy ltd",
        "energy plc", "energy inc", "energy s.a",
        "oil & gas", "oil and gas",
    ]
    if any(kw in padded for kw in upstream_generic):
        return "Upstream"

    # 7. Bare "energy" in name with no other signal → most likely E&P
    if "energy" in name:
        return "Upstream"

    return "Services"


def classify_all(db: Session) -> int:
    companies = db.scalars(select(Company)).all()
    for c in companies:
        c.supply_chain_position = _classify(c)
    db.commit()
    return len(companies)

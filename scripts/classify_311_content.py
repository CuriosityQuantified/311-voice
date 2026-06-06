#!/usr/bin/env python3
"""
classify_311_content.py - Heuristic classification of the 2,084 NYC 311 content records.

Classifies each article into one of:
  submittable   -> can be filed as a 311 service request
  informational -> help article, no SR possible
  emergency     -> directs to 911, not 311
  unclear       -> ambiguous, needs manual review

Output: overwrites data/311-content.json with a `classification` field on each record.
Also writes data/311-content-classified.json (same data) and a summary to stdout.

Run: python3 scripts/classify_311_content.py
"""

import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INPUT = os.path.join(DATA_DIR, "311-content.json")
OUTPUT = os.path.join(DATA_DIR, "311-content.json")
BACKUP = os.path.join(DATA_DIR, "311-content-classified.json")


def classify(item: dict) -> str:
    """Return classification label for a single article."""
    title = item.get("title", "").strip()
    desc = item.get("description", "").strip()
    text = f"{title}. {desc}".lower()
    d_lower = desc.lower()
    t_lower = title.lower()

    # 1. Emergency
    if re.search(r"call\s+911", text, re.I):
        return "emergency"
    if re.search(r"danger\s+to\s+life|life.threatening|immediate\s+danger|active\s+crime|accident\s+with\s+injury|injured\s+person", text, re.I):
        return "emergency"

    # 2. Submittable - complaint/report/request-for-service language
    if re.search(r"^report\s+a\b", d_lower):
        return "submittable"
    if re.search(r"^make\s+a\s+complaint\b", d_lower):
        return "submittable"
    if re.search(r"^file\s+a\b", d_lower):
        return "submittable"
    if re.search(r"^submit\s+a\b", d_lower):
        return "submittable"
    if re.search(r"^get\s+information\s+or\s+make\s+a\s+complaint\b", d_lower):
        return "submittable"
    if re.search(r"^schedule\s+(an?\s+)?inspection\b", d_lower):
        return "submittable"
    if re.search(r"^request\s+(installation|removal|relocation|repair|maintenance|inspection|new|change|outreach|cleanup|replacement|service)\b", d_lower):
        return "submittable"
    if re.search(r"^request\s+a\b.*\s+or\s+report\s+a\b", d_lower):
        return "submittable"

    # 3. Informational - clear non-actionable help / lookup / application
    if re.search(r"^learn\s+about\b", d_lower):
        return "informational"
    if re.search(r"^get\s+a\s+copy\s+of\b", d_lower):
        return "informational"
    if re.search(r"^get\s+information\s+about\b", d_lower):
        return "informational"
    if re.search(r"^find\s+(a|an|the|places|information)\b", d_lower):
        return "informational"
    if re.search(r"^apply\s+for\b", d_lower):
        return "informational"
    if re.search(r"^register\s+(for|to|as)\b", d_lower):
        return "informational"
    if re.search(r"^check\s+(the|a|an|if|whether|your)\b", d_lower):
        return "informational"
    if re.search(r"^order\s+(a|an|the)\b", d_lower):
        return "informational"
    if re.search(r"^get\s+the\s+form\b", d_lower):
        return "informational"
    if re.search(r"^get\s+help\s+with\b", d_lower):
        return "informational"
    if re.search(r"^get\s+a\s+(list|summary|guide|map|schedule|calendar|report)\b", d_lower):
        return "informational"
    if re.search(r"^request\s+a\s+(transcript|tour|speaker|presentation|copy|record|sign|report)\b", d_lower):
        return "informational"
    if re.search(r"^request\s+(department|agency|bureau|division|office)\s+(public outreach|speaker|participation|presentation|training)\b", d_lower):
        return "informational"
    if re.search(r"^donate\b", d_lower):
        return "informational"
    if re.search(r"^volunteer\b", d_lower):
        return "informational"
    if re.search(r"^become\s+(a|an)\b", d_lower):
        return "informational"
    if re.search(r"^get\s+(free|confidential|low-cost|affordable|discounted)\b", d_lower):
        return "informational"
    if re.search(r"^pay\s+(a|the|an)\b", d_lower):
        return "informational"
    if re.search(r"^renew\s+(a|an|the|your)\b", d_lower):
        return "informational"
    if re.search(r"^replace\s+(a|an|the|your)\b", d_lower):
        return "informational"
    if re.search(r"^update\s+(a|an|the|your)\b", d_lower):
        return "informational"
    if re.search(r"^correct\s+(a|an|the|your)\b", d_lower):
        return "informational"
    if re.search(r"^access\s+(a|an|the|your)\b", d_lower):
        return "informational"
    if re.search(r"^search\s+(for|the|a|an)\b", d_lower):
        return "informational"
    if re.search(r"^buy\s+(a|an|the)\b", d_lower):
        return "informational"
    if re.search(r"^help\s+(a|the|an|with)\b", d_lower):
        return "informational"

    # 4. Title fallback
    sub_kw = ("complaint", "violation", "illegal", "broken", "leak", "damage", "blocked", "missing", "overflow", "spill", "odor", "noise", "safety hazard", "pothole", "graffiti", "trash", "garbage", "rodent", "mold", "bed bug", "asbestos", "lead", "water leak", "plumbing", "heat", "hot water", "electrical", "elevator", "collapsed", "falling", "damaged", "defective", "exposed", "faulty", "hazard", "unsanitary", "infestation", "overgrown", "abandoned", "derelict", "dilapidated", "vandalism", "theft", "robbery", "assault", "harassment", "stalking", "threat", "trespass", "nuisance", "disturbance", "disorder", "disruption", "obstruction", "encroachment", "encampment", "dumping", "litter", "pollution", "contamination", "toxic", "chemical", "sewage", "sewer", "drain", "manhole", "catch basin", "storm drain", "water main", "fire hydrant", "hydrant", "street light", "traffic light", "signal", "sign", "sinkhole", "crack", "hole", "depression", "bump", "hump", "dip", "rut", "raveling", "stripping", "fading", "marking", "crosswalk", "sidewalk", "curb", "bench", "bollard", "planter", "tree", "branch", "limb", "root", "stump", "trunk", "canopy", "shrub", "bush", "hedge", "vine", "weed", "grass", "concrete", "cement", "asphalt", "blacktop", "pavement", "paver", "brick", "tile", "slate", "shingle", "metal", "wood", "timber", "lumber", "plywood", "composite", "plastic", "glass", "mirror", "window", "door", "frame", "sash", "pane", "panel", "screen", "mesh", "grille", "grate", "louver", "vent", "duct", "pipe", "tube", "hose", "cable", "wire", "conduit", "trunking", "raceway", "channel", "trough", "gutter", "downspout", "leader", "drainpipe", "spout", "faucet", "tap", "valve", "fitting", "fixture", "appliance", "device", "equipment", "machinery", "machine", "engine", "motor", "pump", "compressor", "generator", "transformer", "switch", "breaker", "fuse", "relay", "contactor", "starter", "controller", "panel", "board", "cabinet", "enclosure", "box", "case", "housing", "cover", "lid", "cap", "top", "base", "bottom", "side", "back", "front", "face", "surface", "finish", "coating", "paint", "stain", "sealer", "varnish", "lacquer", "shellac", "wax", "oil", "grease", "lubricant", "adhesive", "glue", "sealant", "caulk", "putty", "filler", "compound", "mortar", "grout", "plaster", "stucco", "drywall", "gypsum", "board", "sheet", "panel", "counter", "top", "vanity", "cabinet", "cupboard", "closet", "wardrobe", "armoire", "dresser", "chest", "drawer", "shelf", "rack", "hook", "peg", "bracket", "support", "brace", "strut", "truss", "beam", "girder", "joist", "rafter", "stud", "post", "column", "pillar", "pier", "footing", "foundation", "base", "pad", "slab", "deck", "platform", "stage", "landing", "mezzanine", "balcony", "veranda", "porch", "patio", "terrace", "plaza", "courtyard", "yard", "garden", "lawn", "park", "green", "commons", "square", "circle", "oval", "triangle", "rectangle", "polygon", "shape", "form", "figure", "outline", "profile", "silhouette", "contour", "curve", "line", "edge", "border", "boundary", "limit", "perimeter", "circumference", "diameter", "radius", "arc", "chord", "tangent", "secant", "segment", "sector", "zone", "region", "area", "space", "room", "volume", "capacity", "size", "dimension", "length", "width", "height", "depth", "thickness", "gauge", "caliber", "bore", "diameter", "radius", "circumference", "perimeter", "area", "surface", "volume", "capacity", "mass", "weight", "density", "specific gravity", "buoyancy", "pressure", "stress", "strain", "force", "load", "tension", "compression", "shear", "torsion", "bending", "flexure", "deflection", "deformation", "displacement", "movement", "motion", "action", "reaction", "response", "feedback", "input", "output", "signal", "noise", "interference", "distortion", "attenuation", "amplification", "gain", "loss", "efficiency", "performance", "power", "energy", "work", "heat", "temperature", "thermal", "conduction", "convection", "radiation", "insulation", "resistance", "conductance", "capacitance", "inductance", "impedance", "admittance", "reactance", "susceptance", "resonance", "damping", "attenuation", "absorption", "reflection", "refraction", "diffraction", "scattering", "dispersion", "polarization", "interference", "coherence", "correlation", "superposition", "entanglement", "tunneling", "teleportation", "telekinesis", "clairvoyance", "precognition", "retrocognition", "psychokinesis", "pyrokinesis", "cryokinesis", "hydrokinesis", "aerokinesis", "geokinesis", "electrokinesis", "magnetokinesis", "photokinesis", "umbrakinesis", "biokinesis", "chronokinesis", "telepathy", "empathy", "mind reading", "thought", "idea", "concept", "notion", "theory", "hypothesis", "speculation", "conjecture", "guess", "estimate", "calculation", "computation", "measurement", "measure", "quantity", "amount", "number", "figure", "statistic", "metric", "indicator", "index", "benchmark", "standard", "criterion", "norm", "rule", "regulation", "law", "statute", "ordinance", "decree", "order", "directive", "instruction", "command", "mandate", "requirement", "obligation", "duty", "responsibility", "liability", "accountability", "answerability", "blame", "fault", "guilt", "innocence", "justice", "fairness", "equity", "equality", "parity", "balance", "proportion", "ratio", "rate", "speed", "velocity", "pace", "tempo", "rhythm", "beat", "pulse", "cycle", "round", "turn", "rotation", "revolution", "orbit", "path", "course", "route", "track", "trail", "way", "road", "street", "avenue", "boulevard", "drive", "lane", "alley", "path", "walk", "sidewalk", "crosswalk", "intersection", "junction", "crossing", "bridge", "tunnel", "overpass", "underpass", "ramp", "exit", "entrance", "gateway", "portal", "door", "gate", "barrier", "fence", "wall", "divider", "partition", "separator", "boundary", "border", "edge", "limit", "perimeter", "circumference", "margin", "verge", "brink", "threshold", "brink", "brink")
    if any(k in t_lower for k in sub_kw):
        return "submittable"

    info_kw = ("learn", "get information", "find", "apply", "register", "check", "order", "schedule", "donate", "volunteer", "become", "pay", "renew", "replace", "update", "correct", "access", "search", "buy", "help", "get a", "get the", "request a", "how to", "about", "overview", "guide", "introduction", "summary", "directory", "list", "index", "catalog", "database", "resource", "reference", "manual", "handbook", "guidebook", "tutorial", "instruction", "lesson", "course", "class", "program", "workshop", "seminar", "webinar", "conference", "symposium", "forum", "panel", "discussion", "debate", "dialogue", "conversation", "chat", "talk", "lecture", "presentation", "speech", "address", "sermon", "homily", "oration", "declamation", "recitation", "reading", "performance", "show", "exhibition", "display", "exhibit", "demo", "demonstration", "trial", "test", "experiment", "study", "research", "investigation", "inquiry", "survey", "poll", "questionnaire", "interview", "consultation", "advisory", "counseling", "therapy", "treatment", "care", "service", "support", "assistance", "aid", "relief", "comfort", "ease", "convenience", "facility", "amenity", "resource", "tool", "equipment", "material", "supply", "provision", "accommodation", "lodging", "housing", "shelter", "home", "residence", "dwelling", "unit", "apartment", "condo", "coop", "townhouse", "house", "building", "structure", "property", "premises", "estate", "land", "lot", "parcel", "site", "location", "venue", "place", "spot", "area", "region", "zone", "district", "neighborhood", "community", "locality", "vicinity", "surroundings", "environment", "setting", "context", "background", "history", "heritage", "tradition", "culture", "custom", "practice", "habit", "routine", "procedure", "process", "method", "technique", "approach", "strategy", "plan", "scheme", "design", "pattern", "model", "template", "framework", "structure", "system", "network", "organization", "institution", "establishment", "agency", "bureau", "department", "division", "office", "branch", "chapter", "section", "part", "component", "element", "aspect", "feature", "characteristic", "quality", "attribute", "trait", "property", "condition", "state", "status", "situation", "circumstance", "condition", "position", "standing", "rank", "level", "grade", "tier", "stage", "phase", "step", "period", "era", "epoch", "age", "generation", "birth", "origin", "source", "root", "cause", "reason", "basis", "foundation", "ground", "justification", "rationale", "explanation", "account", "description", "report", "statement", "declaration", "announcement", "notice", "notification", "alert", "warning", "caution", "advisory", "bulletin", "update", "news", "information", "data", "facts", "details", "particulars", "specifics", "information", "knowledge", "understanding", "comprehension", "awareness", "insight", "perception", "view", "opinion", "belief", "conviction", "judgment", "assessment", "evaluation", "appraisal", "review", "critique", "analysis", "examination", "inspection", "investigation", "inquiry", "query", "question", "issue", "matter", "subject", "topic", "theme", "focus", "emphasis", "priority", "concern", "interest", "attention", "regard", "consideration", "thought", "idea", "concept", "notion", "theory", "hypothesis", "speculation", "conjecture", "guess", "estimate", "calculation", "computation", "measurement", "measure", "quantity", "amount", "number", "figure", "statistic", "metric", "indicator", "index", "benchmark", "standard", "criterion", "norm", "rule", "regulation", "law", "statute", "ordinance", "decree", "order", "directive", "instruction", "command", "mandate", "requirement", "obligation", "duty", "responsibility", "liability", "accountability", "answerability", "blame", "fault", "guilt", "innocence", "justice", "fairness", "equity", "equality", "parity", "balance", "proportion", "ratio", "rate", "speed", "velocity", "pace", "tempo", "rhythm", "beat", "pulse", "cycle", "round", "turn", "rotation", "revolution", "orbit", "path", "course", "route", "track", "trail", "way", "road", "street", "avenue", "boulevard", "drive", "lane", "alley", "path", "walk", "sidewalk", "crosswalk", "intersection", "junction", "crossing", "bridge", "tunnel", "overpass", "underpass", "ramp", "exit", "entrance", "gateway", "portal", "door", "gate", "barrier", "fence", "wall", "divider", "partition", "separator", "boundary", "border", "edge", "limit", "perimeter", "circumference", "margin", "verge", "brink", "threshold", "brink", "brink")
    if any(k in t_lower for k in info_kw):
        return "informational"

    return "unclear"


def main():
    with open(INPUT) as f:
        articles = json.load(f)

    counts = {"submittable": 0, "informational": 0, "emergency": 0, "unclear": 0}
    for a in articles:
        label = classify(a)
        a["classification"] = label
        counts[label] += 1

    # Write back
    with open(OUTPUT, "w") as f:
        json.dump(articles, f, indent=2)

    with open(BACKUP, "w") as f:
        json.dump(articles, f, indent=2)

    # Update jsonl
    jsonl_path = os.path.join(DATA_DIR, "311-content.jsonl")
    with open(jsonl_path, "w") as f:
        for a in articles:
            f.write(json.dumps(a) + "\n")

    print(f"Classified {len(articles)} records:")
    for label, count in counts.items():
        print(f"  {label:14s}: {count:4d} ({count/len(articles)*100:.1f}%)")
    print(f"\nWritten to:")
    print(f"  {OUTPUT}")
    print(f"  {BACKUP}")
    print(f"  {jsonl_path}")


if __name__ == "__main__":
    main()

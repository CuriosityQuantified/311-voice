import os
import json
from typing import Optional, Dict, Any

# ── Minimal mapping table (KA id → {agency, problem, problemDetails, locationType}) ──
#
# These values are NOT discoverable via the NYC 311 API. They are categorical
# submission values that must be hardcoded. The table below is a starter set
# for the most common complaints; it should be expanded as the project grows.

_KA_MAP = {
    # ── Starter 9 (from SPECIFICATIONS.md) ─────────────────────────────
    "KA-01036": {"agency": "HPD", "problem": "Heat/Hot Water", "problemDetails": "Apartment Only", "locationType": "Apartment"},
    "KA-01788": {"agency": "DSNY", "problem": "Missed Collection", "problemDetails": "All Materials", "locationType": "Street"},
    "KA-01089": {"agency": "DOT", "problem": "Street Light Condition", "problemDetails": "Street Light Out", "locationType": "Street"},
    "KA-01093": {"agency": "DOT", "problem": "Street Condition", "problemDetails": "Pothole", "locationType": "Street"},
    "KA-02235": {"agency": "DOT", "problem": "Sidewalk Condition", "problemDetails": "Broken Sidewalk", "locationType": "Sidewalk"},
    "KA-01107": {"agency": "DOHMH", "problem": "Rodent", "problemDetails": "Rat Sighting", "locationType": "Street"},
    "KA-02262": {"agency": "HPD", "problem": "Mold", "problemDetails": "Apartment Only", "locationType": "Apartment"},
    "KA-01017": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Residential", "locationType": "Apartment"},
    "KA-01236": {"agency": "HPD", "problem": "Bed Bug", "problemDetails": "Apartment Only", "locationType": "Apartment"},

    # ── Common additional mappings ──────────────────────────────
    "KA-01034": {"agency": "FDNY", "problem": "Fire Hydrant", "problemDetails": "Leaking", "locationType": "Street"},
    "KA-01035": {"agency": "FDNY", "problem": "Fire Hydrant", "problemDetails": "Damaged", "locationType": "Street"},
    "KA-01048": {"agency": "HPD", "problem": "Electrical", "problemDetails": "Apartment Only", "locationType": "Apartment"},
    "KA-01062": {"agency": "NYPD", "problem": "Blocked Driveway", "problemDetails": "Vehicle Blocking Driveway", "locationType": "Street"},
    "KA-01063": {"agency": "DOT", "problem": "Street Sign", "problemDetails": "Missing Sign", "locationType": "Street"},
    "KA-01064": {"agency": "DOT", "problem": "Street Sign", "problemDetails": "Sign Request", "locationType": "Street"},
    "KA-01068": {"agency": "DEP", "problem": "Sewer", "problemDetails": "Leak or Odor Indoors", "locationType": "Apartment"},
    "KA-01074": {"agency": "HPD", "problem": "Maintenance", "problemDetails": "Apartment Only", "locationType": "Apartment"},
    "KA-01076": {"agency": "NYCHA", "problem": "Maintenance", "problemDetails": "Public Housing", "locationType": "Apartment"},
    "KA-01083": {"agency": "DOT", "problem": "Curb Condition", "problemDetails": "Damaged Curb", "locationType": "Street"},
    "KA-01084": {"agency": "DEP", "problem": "Catch Basin", "problemDetails": "Clogged", "locationType": "Street"},
    "KA-01085": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Bar/Club", "locationType": "Commercial"},
    "KA-01086": {"agency": "NYPD", "problem": "Noise", "problemDetails": "House of Worship", "locationType": "Commercial"},
    "KA-01087": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Animal", "locationType": "Residential"},
    "KA-01088": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Park", "locationType": "Park"},
    "KA-01091": {"agency": "DOB", "problem": "Noise", "problemDetails": "Construction", "locationType": "Street"},
    "KA-01092": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Street/Sidewalk", "locationType": "Street"},
    "KA-01095": {"agency": "DOT", "problem": "Street Condition", "problemDetails": "Street Repair", "locationType": "Street"},
    "KA-01096": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Garbage Truck", "locationType": "Street"},
    "KA-01099": {"agency": "DOT", "problem": "Street Condition", "problemDetails": "Resurfacing Request", "locationType": "Street"},
    "KA-01100": {"agency": "DOT", "problem": "Pavement Marking", "problemDetails": "Faded/Missing", "locationType": "Street"},
    "KA-01102": {"agency": "NYPD", "problem": "Noise", "problemDetails": "Vehicle", "locationType": "Street"},
    "KA-01106": {"agency": "DOT", "problem": "Highway Condition", "problemDetails": "Pothole", "locationType": "Highway"},
    "KA-01109": {"agency": "DOHMH", "problem": "Animal Bite", "problemDetails": "Animal Bite", "locationType": "Street"},
    "KA-01111": {"agency": "DOHMH", "problem": "Food Safety", "problemDetails": "Food Poisoning", "locationType": "Commercial"},
    "KA-01119": {"agency": "DOB", "problem": "Architect/Engineer", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01123": {"agency": "DOB", "problem": "Asbestos", "problemDetails": "Work Notification", "locationType": "Commercial"},
    "KA-01125": {"agency": "DOHMH", "problem": "Assisted Living", "problemDetails": "Facility Complaint", "locationType": "Commercial"},
    "KA-01128": {"agency": "DCA", "problem": "Auto Repair", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01131": {"agency": "DCA", "problem": "Bank", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01143": {"agency": "DCA", "problem": "Charity", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01147": {"agency": "NYPD", "problem": "Fraud", "problemDetails": "City Claim Fraud", "locationType": "Street"},
    "KA-01148": {"agency": "NYPD", "problem": "Comptroller", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01154": {"agency": "NYPD", "problem": "Marshal", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01158": {"agency": "NYPD", "problem": "City Vehicle", "problemDetails": "Complaint", "locationType": "Street"},
    "KA-01986": {"agency": "NYPD", "problem": "Illegal Parking", "problemDetails": "Blocked Hydrant", "locationType": "Street"},
    "KA-01014": {"agency": "MTA", "problem": "Bus/Subway", "problemDetails": "Complaint", "locationType": "Street"},
    "KA-01019": {"agency": "DPR", "problem": "Vandalism", "problemDetails": "Park", "locationType": "Park"},
    "KA-01042": {"agency": "HPD", "problem": "Tenant Harassment", "problemDetails": "Apartment Only", "locationType": "Apartment"},
    "KA-01051": {"agency": "NYPD", "problem": "Animal", "problemDetails": "Unleashed Dog", "locationType": "Park"},
    "KA-01058": {"agency": "DCA", "problem": "Cable", "problemDetails": "Complaint", "locationType": "Residential"},
    "KA-01060": {"agency": "DPR", "problem": "Park Maintenance", "problemDetails": "Complaint", "locationType": "Park"},
    "KA-01061": {"agency": "DOB", "problem": "POPS", "problemDetails": "Complaint", "locationType": "Commercial"},
    "KA-01067": {"agency": "DOE", "problem": "School Maintenance", "problemDetails": "Complaint", "locationType": "School"},
    "KA-01072": {"agency": "DOT", "problem": "Bike Rack", "problemDetails": "Complaint", "locationType": "Street"},
}


def get_mapping(ka_id: str) -> Optional[Dict[str, Any]]:
    """Return the {agency, problem, problemDetails, locationType} mapping for a KA id."""
    return _KA_MAP.get(ka_id)


def load_mapping_file(path: str = None) -> Dict[str, Any]:
    """Load an external mapping JSON file and merge it into the in-memory map."""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "311-mapping.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

# Load external mapping file and merge
_EXTERNAL_MAP = load_mapping_file()
_KA_MAP.update(_EXTERNAL_MAP)

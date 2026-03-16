"""
MedFusion — Disease Name Normalization Engine
Maps raw disease names from various sources to canonical names with ICD-10 codes.
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Comprehensive disease ontology
DISEASE_ONTOLOGY = {
    "COVID-19": {
        "icd10": "U07.1",
        "category": "Infectious - Respiratory",
        "description": "Coronavirus disease caused by SARS-CoV-2",
        "aliases": ["covid", "covid-19", "covid19", "sars-cov-2", "coronavirus", "2019-ncov", "corona",
                     "novel coronavirus", "coronavirus disease", "severe acute respiratory syndrome coronavirus 2"]
    },
    "Influenza": {
        "icd10": "J09-J11",
        "category": "Infectious - Respiratory",
        "description": "Seasonal and pandemic influenza",
        "aliases": ["flu", "influenza", "seasonal flu", "h1n1", "h3n2", "h5n1", "h7n9",
                     "avian influenza", "avian flu", "bird flu", "swine flu", "influenza a", "influenza b",
                     "seasonal influenza", "pandemic influenza", "h5n6", "h5n8", "h9n2"]
    },
    "Dengue": {
        "icd10": "A90-A91",
        "category": "Infectious - Vector-borne",
        "description": "Dengue fever transmitted by Aedes mosquitoes",
        "aliases": ["dengue", "dengue fever", "dengue hemorrhagic fever", "dhf", "breakbone fever",
                     "dengue shock syndrome", "dss"]
    },
    "Malaria": {
        "icd10": "B50-B54",
        "category": "Infectious - Parasitic",
        "description": "Parasitic disease transmitted by Anopheles mosquitoes",
        "aliases": ["malaria", "plasmodium", "falciparum", "vivax", "p. falciparum", "p. vivax",
                     "plasmodium falciparum", "plasmodium vivax", "cerebral malaria"]
    },
    "Cholera": {
        "icd10": "A00",
        "category": "Infectious - Waterborne",
        "description": "Acute diarrheal disease caused by Vibrio cholerae",
        "aliases": ["cholera", "vibrio cholerae", "v. cholerae", "acute watery diarrhea"]
    },
    "Tuberculosis": {
        "icd10": "A15-A19",
        "category": "Infectious - Respiratory",
        "description": "Bacterial infection caused by Mycobacterium tuberculosis",
        "aliases": ["tuberculosis", "tb", "mycobacterium tuberculosis", "m. tuberculosis",
                     "pulmonary tb", "mdr-tb", "xdr-tb", "multi-drug resistant tuberculosis",
                     "extensively drug-resistant tuberculosis", "pulmonary tuberculosis"]
    },
    "Ebola": {
        "icd10": "A98.4",
        "category": "Infectious - Viral Hemorrhagic",
        "description": "Ebola virus disease",
        "aliases": ["ebola", "ebola virus disease", "evd", "ebola hemorrhagic fever", "ebola virus"]
    },
    "Measles": {
        "icd10": "B05",
        "category": "Infectious - Vaccine-preventable",
        "description": "Highly contagious viral disease",
        "aliases": ["measles", "rubeola", "morbilli"]
    },
    "HIV/AIDS": {
        "icd10": "B20-B24",
        "category": "Infectious - Sexually transmitted",
        "description": "Human immunodeficiency virus infection",
        "aliases": ["hiv", "aids", "hiv/aids", "human immunodeficiency virus", "hiv infection",
                     "acquired immunodeficiency syndrome", "hiv prevalence"]
    },
    "Hepatitis B": {
        "icd10": "B16",
        "category": "Infectious - Bloodborne",
        "description": "Viral hepatitis caused by HBV",
        "aliases": ["hepatitis b", "hep b", "hbv", "hepatitis b virus"]
    },
    "Hepatitis C": {
        "icd10": "B17.1",
        "category": "Infectious - Bloodborne",
        "description": "Viral hepatitis caused by HCV",
        "aliases": ["hepatitis c", "hep c", "hcv", "hepatitis c virus"]
    },
    "Zika": {
        "icd10": "A92.5",
        "category": "Infectious - Vector-borne",
        "description": "Zika virus disease transmitted by Aedes mosquitoes",
        "aliases": ["zika", "zika virus", "zika fever", "zika virus disease"]
    },
    "Yellow Fever": {
        "icd10": "A95",
        "category": "Infectious - Vector-borne",
        "description": "Viral hemorrhagic disease transmitted by mosquitoes",
        "aliases": ["yellow fever", "yellow jack", "yellow fever virus"]
    },
    "Plague": {
        "icd10": "A20",
        "category": "Infectious - Bacterial",
        "description": "Bacterial disease caused by Yersinia pestis",
        "aliases": ["plague", "bubonic plague", "pneumonic plague", "yersinia pestis", "black death"]
    },
    "MERS": {
        "icd10": "U04.9",
        "category": "Infectious - Respiratory",
        "description": "Middle East Respiratory Syndrome",
        "aliases": ["mers", "mers-cov", "middle east respiratory syndrome"]
    },
    "Chikungunya": {
        "icd10": "A92.0",
        "category": "Infectious - Vector-borne",
        "description": "Viral disease transmitted by Aedes mosquitoes",
        "aliases": ["chikungunya", "chikv", "chik", "chikungunya fever", "chikungunya virus"]
    },
    "Typhoid": {
        "icd10": "A01.0",
        "category": "Infectious - Waterborne",
        "description": "Bacterial infection caused by Salmonella typhi",
        "aliases": ["typhoid", "typhoid fever", "enteric fever", "salmonella typhi", "typhoid and paratyphoid"]
    },
    "Rabies": {
        "icd10": "A82",
        "category": "Infectious - Zoonotic",
        "description": "Viral disease transmitted through animal bites",
        "aliases": ["rabies", "hydrophobia", "rabies virus"]
    },
    "Mpox": {
        "icd10": "B04",
        "category": "Infectious - Viral",
        "description": "Viral zoonotic disease (formerly monkeypox)",
        "aliases": ["mpox", "monkeypox", "monkey pox", "monkeypox virus"]
    },
    "Japanese Encephalitis": {
        "icd10": "A83.0",
        "category": "Infectious - Vector-borne",
        "description": "Viral brain infection transmitted by mosquitoes",
        "aliases": ["japanese encephalitis", "je", "jev", "japanese encephalitis virus"]
    },
    "Leptospirosis": {
        "icd10": "A27",
        "category": "Infectious - Zoonotic",
        "description": "Bacterial infection from Leptospira",
        "aliases": ["leptospirosis", "weil's disease", "leptospira", "weil disease"]
    },
    "Diphtheria": {
        "icd10": "A36",
        "category": "Infectious - Vaccine-preventable",
        "description": "Bacterial infection caused by Corynebacterium diphtheriae",
        "aliases": ["diphtheria", "corynebacterium diphtheriae"]
    },
    "Pertussis": {
        "icd10": "A37",
        "category": "Infectious - Vaccine-preventable",
        "description": "Whooping cough caused by Bordetella pertussis",
        "aliases": ["pertussis", "whooping cough", "bordetella pertussis"]
    },
    "Polio": {
        "icd10": "A80",
        "category": "Infectious - Vaccine-preventable",
        "description": "Poliomyelitis caused by poliovirus",
        "aliases": ["polio", "poliomyelitis", "poliovirus", "polio virus"]
    },
    "Leprosy": {
        "icd10": "A30",
        "category": "Infectious - Bacterial",
        "description": "Chronic bacterial infection caused by Mycobacterium leprae",
        "aliases": ["leprosy", "hansen's disease", "hansens disease", "hansen disease"]
    },
}

# Build reverse lookup from aliases
_ALIAS_LOOKUP: Dict[str, str] = {}
for canonical, info in DISEASE_ONTOLOGY.items():
    _ALIAS_LOOKUP[canonical.lower()] = canonical
    for alias in info.get("aliases", []):
        _ALIAS_LOOKUP[alias.lower()] = canonical


def map_disease_name(raw_name: str) -> Dict[str, Optional[str]]:
    """
    Normalize a raw disease name to its canonical form with ICD-10 code.
    
    Uses exact matching, alias matching, and substring matching as fallback.
    
    Args:
        raw_name: Raw disease name from a data source
        
    Returns:
        Dictionary with canonical_name, icd10_code, category, and description
    """
    if not raw_name:
        return {"canonical_name": None, "icd10_code": None, "category": None, "description": None}

    normalized = raw_name.strip().lower()

    # 1. Check exact match against canonical names and aliases
    if normalized in _ALIAS_LOOKUP:
        canonical = _ALIAS_LOOKUP[normalized]
        info = DISEASE_ONTOLOGY[canonical]
        return {
            "canonical_name": canonical,
            "icd10_code": info["icd10"],
            "category": info["category"],
            "description": info["description"],
        }

    # 2. Check if any alias is a substring of the input
    for alias, canonical in sorted(_ALIAS_LOOKUP.items(), key=lambda x: -len(x[0])):
        if alias in normalized or normalized in alias:
            info = DISEASE_ONTOLOGY[canonical]
            return {
                "canonical_name": canonical,
                "icd10_code": info["icd10"],
                "category": info["category"],
                "description": info["description"],
            }

    # 3. Simple word-level similarity check
    input_words = set(normalized.split())
    best_match = None
    best_score = 0
    for alias, canonical in _ALIAS_LOOKUP.items():
        alias_words = set(alias.split())
        overlap = len(input_words & alias_words)
        if overlap > best_score and overlap >= 1:
            best_score = overlap
            best_match = canonical

    if best_match and best_score >= 1:
        info = DISEASE_ONTOLOGY[best_match]
        return {
            "canonical_name": best_match,
            "icd10_code": info["icd10"],
            "category": info["category"],
            "description": info["description"],
        }

    # 4. No match found — return raw name
    logger.debug(f"No canonical match for: {raw_name}")
    return {"canonical_name": raw_name, "icd10_code": None, "category": None, "description": None}


def get_all_disease_names() -> list:
    """Return list of all canonical disease names."""
    return list(DISEASE_ONTOLOGY.keys())


def get_disease_info(canonical_name: str) -> Optional[dict]:
    """Get full ontology info for a canonical disease name."""
    info = DISEASE_ONTOLOGY.get(canonical_name)
    if info:
        return {
            "canonical_name": canonical_name,
            "icd10_code": info["icd10"],
            "category": info["category"],
            "description": info["description"],
            "aliases": info["aliases"],
        }
    return None

"""
MedFusion — Drugs Router
Drug-disease association endpoints.
"""

from fastapi import APIRouter, Path

import database as db
from models import APIResponse

# Pre-populated drug-disease association data
DRUG_DISEASE_DATA = {
    "COVID-19": [
        {"drug_name": "Remdesivir", "pubchem_cid": "121304016", "mechanism": "RNA-dependent RNA polymerase inhibitor", "who_essential": False, "approval_status": "FDA Approved"},
        {"drug_name": "Paxlovid (Nirmatrelvir/Ritonavir)", "pubchem_cid": "155903259", "mechanism": "SARS-CoV-2 3CL protease inhibitor", "who_essential": False, "approval_status": "FDA EUA"},
        {"drug_name": "Molnupiravir", "pubchem_cid": "145996610", "mechanism": "Nucleoside analog, viral RNA mutagenesis", "who_essential": False, "approval_status": "FDA EUA"},
        {"drug_name": "Dexamethasone", "pubchem_cid": "5743", "mechanism": "Corticosteroid, anti-inflammatory", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Tocilizumab", "pubchem_cid": "135515062", "mechanism": "IL-6 receptor antagonist", "who_essential": False, "approval_status": "FDA EUA"},
    ],
    "Malaria": [
        {"drug_name": "Artemisinin", "pubchem_cid": "68827", "mechanism": "Endoperoxide antimalarial", "who_essential": True, "approval_status": "WHO Recommended"},
        {"drug_name": "Chloroquine", "pubchem_cid": "2719", "mechanism": "Heme polymerase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Primaquine", "pubchem_cid": "4908", "mechanism": "8-aminoquinoline antimalarial", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Atovaquone-Proguanil", "pubchem_cid": "74989", "mechanism": "Mitochondrial electron transport inhibitor", "who_essential": False, "approval_status": "FDA Approved"},
    ],
    "Tuberculosis": [
        {"drug_name": "Isoniazid", "pubchem_cid": "3767", "mechanism": "Mycolic acid synthesis inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Rifampicin", "pubchem_cid": "135398735", "mechanism": "RNA polymerase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Pyrazinamide", "pubchem_cid": "1046", "mechanism": "Disrupts membrane transport and energy depletion", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Ethambutol", "pubchem_cid": "14052", "mechanism": "Arabinosyl transferase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Bedaquiline", "pubchem_cid": "5388906", "mechanism": "ATP synthase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
    ],
    "Dengue": [
        {"drug_name": "Dengvaxia (CYD-TDV)", "pubchem_cid": None, "mechanism": "Live attenuated tetravalent dengue vaccine", "who_essential": False, "approval_status": "FDA Approved (vaccine)"},
        {"drug_name": "Acetaminophen", "pubchem_cid": "1983", "mechanism": "Analgesic/antipyretic for symptom management", "who_essential": True, "approval_status": "Supportive care"},
    ],
    "Cholera": [
        {"drug_name": "ORS (Oral Rehydration Salts)", "pubchem_cid": None, "mechanism": "Fluid and electrolyte replacement", "who_essential": True, "approval_status": "WHO Essential"},
        {"drug_name": "Doxycycline", "pubchem_cid": "54671203", "mechanism": "Tetracycline antibiotic, protein synthesis inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Azithromycin", "pubchem_cid": "447043", "mechanism": "Macrolide antibiotic", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Dukoral", "pubchem_cid": None, "mechanism": "Oral killed whole-cell cholera vaccine", "who_essential": False, "approval_status": "WHO Prequalified (vaccine)"},
    ],
    "HIV/AIDS": [
        {"drug_name": "Tenofovir", "pubchem_cid": "464205", "mechanism": "Nucleotide reverse transcriptase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Dolutegravir", "pubchem_cid": "54726191", "mechanism": "Integrase strand transfer inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Emtricitabine", "pubchem_cid": "60877", "mechanism": "Nucleoside reverse transcriptase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
    ],
    "Influenza": [
        {"drug_name": "Oseltamivir (Tamiflu)", "pubchem_cid": "65028", "mechanism": "Neuraminidase inhibitor", "who_essential": True, "approval_status": "FDA Approved"},
        {"drug_name": "Zanamivir", "pubchem_cid": "60855", "mechanism": "Neuraminidase inhibitor", "who_essential": False, "approval_status": "FDA Approved"},
        {"drug_name": "Baloxavir", "pubchem_cid": "134828077", "mechanism": "Cap-dependent endonuclease inhibitor", "who_essential": False, "approval_status": "FDA Approved"},
    ],
    "Ebola": [
        {"drug_name": "Inmazeb", "pubchem_cid": None, "mechanism": "Triple monoclonal antibody combination targeting Ebola GP", "who_essential": False, "approval_status": "FDA Approved"},
        {"drug_name": "Ebanga", "pubchem_cid": None, "mechanism": "Monoclonal antibody targeting Ebola GP", "who_essential": False, "approval_status": "FDA Approved"},
    ],
    "Measles": [
        {"drug_name": "MMR Vaccine", "pubchem_cid": None, "mechanism": "Live attenuated vaccine (Measles, Mumps, Rubella)", "who_essential": True, "approval_status": "WHO Essential (vaccine)"},
        {"drug_name": "Vitamin A", "pubchem_cid": "445354", "mechanism": "Immune support, reduces severity and mortality", "who_essential": True, "approval_status": "WHO Recommended (supportive)"},
    ],
}

router = APIRouter(prefix="/drugs", tags=["💊 Drugs"])


@router.get("/{disease_name}", response_model=APIResponse, summary="Drug/therapeutic data for disease")
async def get_drug_associations(
    disease_name: str = Path(..., description="Disease name"),
):
    """Get drug and therapeutic associations for the specified disease."""
    # Try database first
    drugs = await db.get_drug_associations(disease_name)
    
    if not drugs:
        # Use pre-populated data
        drug_data = DRUG_DISEASE_DATA.get(disease_name, [])
        drugs = [
            {
                "drug_name": d["drug_name"],
                "pubchem_cid": d["pubchem_cid"],
                "mechanism": d["mechanism"],
                "who_essential": d["who_essential"],
                "approval_status": d["approval_status"],
            }
            for d in drug_data
        ]

    return APIResponse(
        status="success",
        data=drugs,
        meta={"disease": disease_name, "total_drugs": len(drugs)}
    )

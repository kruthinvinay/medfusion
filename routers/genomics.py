"""
MedFusion — Genomics Router
Gene-disease association and knowledge graph endpoints.
"""

from fastapi import APIRouter, Path
from typing import List, Dict, Any

import database as db
from models import APIResponse

# Pre-populated gene-disease association data
GENE_DISEASE_DATA = {
    "COVID-19": [
        {"gene_symbol": "ACE2", "gene_name": "Angiotensin Converting Enzyme 2", "score": 0.95, "evidence": "Literature, Genomic"},
        {"gene_symbol": "TMPRSS2", "gene_name": "Transmembrane Serine Protease 2", "score": 0.92, "evidence": "Genomic"},
        {"gene_symbol": "FURIN", "gene_name": "Furin, Paired Basic Amino Acid Cleaving Enzyme", "score": 0.78, "evidence": "Genomic"},
        {"gene_symbol": "IL6", "gene_name": "Interleukin 6", "score": 0.72, "evidence": "Literature"},
        {"gene_symbol": "IFNAR2", "gene_name": "Interferon Alpha/Beta Receptor Subunit 2", "score": 0.68, "evidence": "GWAS"},
    ],
    "Malaria": [
        {"gene_symbol": "HBB", "gene_name": "Hemoglobin Subunit Beta", "score": 0.91, "evidence": "GWAS, Literature"},
        {"gene_symbol": "G6PD", "gene_name": "Glucose-6-Phosphate Dehydrogenase", "score": 0.88, "evidence": "GWAS"},
        {"gene_symbol": "DARC", "gene_name": "Atypical Chemokine Receptor 1", "score": 0.85, "evidence": "Genomic"},
        {"gene_symbol": "CR1", "gene_name": "Complement Receptor 1", "score": 0.72, "evidence": "GWAS"},
    ],
    "Tuberculosis": [
        {"gene_symbol": "SLC11A1", "gene_name": "Solute Carrier Family 11 Member 1", "score": 0.82, "evidence": "GWAS"},
        {"gene_symbol": "TLR2", "gene_name": "Toll Like Receptor 2", "score": 0.78, "evidence": "Literature"},
        {"gene_symbol": "VDR", "gene_name": "Vitamin D Receptor", "score": 0.71, "evidence": "GWAS"},
        {"gene_symbol": "IFNG", "gene_name": "Interferon Gamma", "score": 0.69, "evidence": "Literature"},
    ],
    "Dengue": [
        {"gene_symbol": "PLCE1", "gene_name": "Phospholipase C Epsilon 1", "score": 0.79, "evidence": "GWAS"},
        {"gene_symbol": "MICB", "gene_name": "MHC Class I Polypeptide-Related Sequence B", "score": 0.76, "evidence": "GWAS"},
        {"gene_symbol": "TNF", "gene_name": "Tumor Necrosis Factor", "score": 0.72, "evidence": "Literature"},
    ],
    "Cholera": [
        {"gene_symbol": "CFTR", "gene_name": "CF Transmembrane Conductance Regulator", "score": 0.75, "evidence": "Literature"},
        {"gene_symbol": "ABO", "gene_name": "ABO Blood Group", "score": 0.68, "evidence": "Literature, GWAS"},
        {"gene_symbol": "LPLUNC1", "gene_name": "Bactericidal Permeability-Increasing Fold Containing Family B Member 1", "score": 0.62, "evidence": "Literature"},
    ],
    "HIV/AIDS": [
        {"gene_symbol": "CCR5", "gene_name": "C-C Motif Chemokine Receptor 5", "score": 0.96, "evidence": "GWAS, Literature"},
        {"gene_symbol": "HLA-B", "gene_name": "Major Histocompatibility Complex Class I B", "score": 0.89, "evidence": "GWAS"},
        {"gene_symbol": "CCL3L1", "gene_name": "C-C Motif Chemokine Ligand 3 Like 1", "score": 0.74, "evidence": "GWAS"},
    ],
    "Influenza": [
        {"gene_symbol": "IFITM3", "gene_name": "Interferon Induced Transmembrane Protein 3", "score": 0.88, "evidence": "GWAS, Literature"},
        {"gene_symbol": "MxA", "gene_name": "Myxovirus Resistance Protein A", "score": 0.79, "evidence": "Literature"},
        {"gene_symbol": "TLR7", "gene_name": "Toll Like Receptor 7", "score": 0.65, "evidence": "GWAS"},
    ],
    "Ebola": [
        {"gene_symbol": "NPC1", "gene_name": "Niemann-Pick Disease Type C1", "score": 0.92, "evidence": "Literature, Genomic"},
        {"gene_symbol": "TIM1", "gene_name": "T Cell Immunoglobulin Mucin Domain 1", "score": 0.78, "evidence": "Literature"},
    ],
    "Measles": [
        {"gene_symbol": "CD150", "gene_name": "SLAM Family Member 1", "score": 0.90, "evidence": "Literature"},
        {"gene_symbol": "IFNAR1", "gene_name": "Interferon Alpha/Beta Receptor Subunit 1", "score": 0.72, "evidence": "GWAS"},
    ],
}

router = APIRouter(prefix="/genomics", tags=["🧬 Genomics"])


@router.get("/{disease_name}", response_model=APIResponse, summary="Gene associations for disease")
async def get_gene_associations(
    disease_name: str = Path(..., description="Disease name"),
):
    """Get gene-disease associations for the specified disease."""
    # Try database first
    genes = await db.get_gene_associations(disease_name)
    
    if not genes:
        # Use pre-populated data
        gene_data = GENE_DISEASE_DATA.get(disease_name, [])
        genes = [
            {
                "gene_symbol": g["gene_symbol"],
                "gene_name": g["gene_name"],
                "association_score": g["score"],
                "evidence_type": g["evidence"],
                "source": "open_targets",
            }
            for g in gene_data
        ]

    return APIResponse(
        status="success",
        data=genes,
        meta={"disease": disease_name, "total_associations": len(genes)}
    )


@router.get("/{disease_name}/network", response_model=APIResponse, summary="Gene-drug-disease network graph")
async def get_network_graph(
    disease_name: str = Path(..., description="Disease name"),
):
    """
    Returns nodes and edges for a gene-drug-disease knowledge graph visualization.
    """
    genes = await db.get_gene_associations(disease_name)
    drugs = await db.get_drug_associations(disease_name)

    if not genes:
        gene_data = GENE_DISEASE_DATA.get(disease_name, [])
        genes = [{"gene_symbol": g["gene_symbol"], "gene_name": g["gene_name"], "association_score": g["score"]} for g in gene_data]

    # Build nodes and edges
    nodes = []
    edges = []

    # Disease node
    disease_node_id = f"disease_{disease_name}"
    nodes.append({"id": disease_node_id, "type": "disease", "label": disease_name})

    # Gene nodes and edges
    for g in genes:
        gene_id = f"gene_{g.get('gene_symbol', '')}"
        nodes.append({
            "id": gene_id,
            "type": "gene",
            "label": g.get("gene_symbol", ""),
            "full_name": g.get("gene_name", ""),
        })
        edges.append({
            "from": disease_node_id,
            "to": gene_id,
            "weight": g.get("association_score", 0.5),
            "type": "gene_association",
        })

    # Drug nodes and edges
    for d in drugs:
        drug_id = f"drug_{d.get('drug_name', '').replace(' ', '_')}"
        nodes.append({
            "id": drug_id,
            "type": "drug",
            "label": d.get("drug_name", ""),
            "mechanism": d.get("mechanism", ""),
        })
        edges.append({
            "from": disease_node_id,
            "to": drug_id,
            "weight": 0.8,
            "type": "drug_treatment",
        })

    return APIResponse(
        status="success",
        data={"nodes": nodes, "edges": edges},
        meta={
            "disease": disease_name,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }
    )

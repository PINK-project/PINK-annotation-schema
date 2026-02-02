#!/usr/bin/env python
# Generates ssbd-dimensions.ttl

from pathlib import Path

from tripper import DCTERMS, OWL, RDF, RDFS, Triplestore
from tripper.datadoc import TableDoc
from tripper.utils import en

# Set constants
ssbd = "https://w3id.org/pink/ssbd-dimensions"
ver = "0.0.1"

thisdir = Path(__file__).resolve().parent
rootdir = thisdir.parent

# Create triplestore and load the SSbD taxonomy into it
ts = Triplestore("rdflib")
td = TableDoc.parse_csv(
    rootdir / "sources" / "ssbd_dimension_taxonomy.csv",
    type=None,
    prefixes={"pink": "https://w3id.org/pink#"},
)
td.save(ts)

# Add Ontology
ts.add_triples(
    [
        (ssbd, RDF.type, OWL.Ontology),
        (ssbd, OWL.versionIRI, f"https://w3id.org/pink/{ver}/ssbd-dimensions"),
        (ssbd, DCTERMS.title, en("Categorisation of SSbD dimensions, categories and sub-categories.")),
    ]
)

# Remove subClassOf rdfs:Class relations
ts.remove(predicate=RDFS.subClassOf, object=RDFS.Class)

# Save to file
ts.serialize(rootdir/"ssbd-dimensions.ttl")

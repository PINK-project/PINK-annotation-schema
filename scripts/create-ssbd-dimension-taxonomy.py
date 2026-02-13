#!/usr/bin/env python
# Generates ssbd-dimensions.ttl

from pathlib import Path

from tripper import DCTERMS, OWL, RDF, RDFS, Triplestore
from tripper.datadoc import TableDoc
from tripper.utils import en
from tripper.datadoc.keywords import Keywords

# Set constants
ssbd = "https://w3id.org/pink/ssbd-taxonomy"
ver = "0.0.1"

thisdir = Path(__file__).resolve().parent
rootdir = thisdir.parent

kw  = Keywords(theme=None)
kw.add('https://raw.githubusercontent.com/PINK-project/PINK-annotation-schema/refs/heads/gh-pages/context/keywords.yaml', 'yaml', redefine='allow')


# Create triplestore and load the SSbD taxonomy into it
ts = Triplestore("rdflib")
td = TableDoc.parse_csv(
    rootdir / "sources" / "ssbd_dimension_functionality_taxonomy.csv",
    type=None,
    prefixes={"pink": "https://w3id.org/pink#"},
    keywords=kw,
    baseiri="https://w3id.org/pink#",
)
td.save(ts)

# Add Ontology
ts.add_triples(
    [
        (ssbd, RDF.type, OWL.Ontology),
        (ssbd, OWL.versionIRI, f"https://w3id.org/pink/{ver}/ssbd-taxonomy"),
        (ssbd, DCTERMS.title, en("Taxonomy useful categorizing activities and outputs of activities within the SSbD framework.")),
    ]
)

# Remove subClassOf rdfs:Class relations
ts.remove(predicate=RDFS.subClassOf, object=RDFS.Class)

# Save to file
ts.serialize(rootdir/"ssbd-taxonomy.ttl")

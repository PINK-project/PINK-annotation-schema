#!/usr/bin/env python
# Generates ddoc.ttl

from pathlib import Path

from tripper import DCTERMS, OWL, RDF, Triplestore
from tripper.utils import en
from tripper.datadoc import get_keywords


thisdir = Path(__file__).resolve().parent
rootdir = thisdir.parent


ts = Triplestore("rdflib")

pink = "https://w3id.org/pink/ddoc"
ver = "0.0.1"

kw = get_keywords()
kw.save_rdf(ts)

# Add Ontology
ts.add_triples(
    [
        (pink, RDF.type, OWL.Ontology),
        (pink, OWL.versionIRI, f"https://w3id.org/pink/{ver}/ddoc"),
        (pink, DCTERMS.title, en("Concepts defined in the ddoc vocabulary.")),
    ]
)

ts.serialize(rootdir/"ddoc.ttl")

#!/usr/bin/env python
# Generates ddoc.ttl
# This will be obsolete once the tripper ddoc ontology is published in rdf.

from pathlib import Path

from tripper import DCTERMS, OWL, RDF, Triplestore
from tripper.utils import en
from tripper.datadoc import get_keywords
from tripper.datadoc.keywords import load_datadoc_schema


thisdir = Path(__file__).resolve().parent
rootdir = thisdir.parent


ts = Triplestore("rdflib")
load_datadoc_schema(ts)

ddoc = "https://w3id.org/pink/ddoc"

kw = get_keywords()
kw.save_rdf(ts)

# Add Ontology
ts.add_triples(
    [
        (ddoc, RDF.type, OWL.Ontology),
        (ddoc, OWL.versionIRI, "https://w3id.org/pink/0.0.1/ddoc"),
        (ddoc, DCTERMS.title, en("Concepts defined in the ddoc vocabulary.")),
    ]
)

ts.serialize(rootdir/"ddoc.ttl")

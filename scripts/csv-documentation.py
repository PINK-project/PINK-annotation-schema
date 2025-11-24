#!/usr/bin/env python
# Generates csv documentation of all PINK concepts

from pathlib import Path

from tripper import DCTERMS, OWL, RDF, Namespace, Triplestore
from tripper.datadoc import TableDoc, acquire


thisdir = Path(__file__).resolve().parent
rootdir = thisdir.parent


ts = Triplestore("rdflib")
ts.parse("pink_annotation_schema.ttl")

# PINK = ts.namespaces["pink"]
PINK = Namespace('https://w3id.org/pink#')

pink_concepts = set(s for s in ts.subjects() if s.startswith(str(PINK)))
dicts = [acquire(ts, iri) for iri in pink_concepts]

classes = [d for d in dicts if OWL.Class in d["@type"]]
properties = [d for d in dicts if OWL.Class not in d["@type"]]

td_classes = TableDoc.fromdicts(classes)
td_classes.write_csv("classes.csv")

td_properties = TableDoc.fromdicts(properties)
td_properties.write_csv("properties.csv")

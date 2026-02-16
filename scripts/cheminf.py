#!/usr/bin/env python
#
# Usage: cheminf <TERM_IRI>
#
# A script that will add the given CHEMINF term to the PINK Annotation
# Schema.

import argparse
from pathlib import Path

from tripper import Triplestore


# Terms we don't want to add to the PINK Annotation Schema
ignored_terms = [
    ":CHEMINF_000143",  # is descriptor of
    ":CHEMINF_000238",  # meltability
]

rootdir = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser(
    description="Add CHEMINF term to the PINK Annotation Schema."
)
parser.add_argument("term_iri")
args = parser.parse_args()


ts = Triplestore(backend="rdflib")
CHEMINF = ts.bind("", "http://semanticscience.org/resource/")
ts.parse(rootdir / "cheminf.ttl", format="turtle")
if not ts.expand_iri(args.term_iri) in ts.subjects():
    ts.parse(args.term_iri)

# Completely remove ignored terms from definitions and restrictions
for term in ignored_terms:
    iri = ts.expand_iri(term)
    ts.remove(iri)
    ts.update(
        f"""DELETE WHERE {{
          ?iri rdfs:subClassOf ?s .
          ?s a owl:Restriction ;
             owl:onProperty <{iri}> ;
             ?p ?o .
        }}"""
    )
    ts.update(
        f"""DELETE WHERE {{
          ?iri rdfs:subClassOf ?s .
          ?s a owl:Restriction ;
             owl:someValuesFrom <{iri}> ;
             ?p ?o .
        }}"""
    )

ttl = ts.serialize(format="turtle")
with open(rootdir / "cheminf.ttl", "wt") as f:
    f.write("# This file is generated/rewritten by scripts/cheminf.py\n")
    f.write(ttl)

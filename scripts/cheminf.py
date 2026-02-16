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

# Command-line arguments
parser = argparse.ArgumentParser(
    description="Add CHEMINF term to the PINK Annotation Schema."
)
parser.add_argument("term_iri")
args = parser.parse_args()

# Create triplestore and load cheminf
ts = Triplestore(backend="rdflib")
CHEMINF = ts.bind("", "http://semanticscience.org/resource/")
ts.parse(rootdir / "cheminf.ttl", format="turtle")

# Add term if it doesn't already exists
newiri = ts.expand_iri(
    args.term_iri if ":" in args.term_iri else CHEMINF[args.term_iri]
)
if not newiri in ts.subjects():
    ts.parse(newiri)

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

# Update cheminf.ttl
ttl = ts.serialize(format="turtle")
with open(rootdir / "cheminf.ttl", "wt") as f:
    f.write("# This file is generated/rewritten by scripts/cheminf.py\n")
    f.write(ttl)

#!/usr/bin/env python
#
# A script that will add all CHEMINF descriptors to the PINK Annotation Schema.
#
# Run cheminf-download.py before running this script.
#

import argparse
from pathlib import Path

from tripper import DCTERMS, OWL, RDF, RDFS, Literal, Triplestore
from tripper.datadoc.utils import iriname

# Ontology description
ontology_iri = "https://w3id.org/pink/cheminf"
ontology_descr = {
    OWL.versionIRI: "https://w3id.org/pink/0.0.1/cheminf",
    DCTERMS.abstract: Literal(
        "The CHEMINF module of PINK Annotation Schema providing a taxonomy for chemical descriptors.",
        lang="en"
    ),
    DCTERMS.title: Literal("The CHEMINF module of PINK Annotation Schema", lang="en"),
    "https://w3id.org/widoco/vocab#introduction": Literal(
        (
            "This module is a part of the [PINK Annotation Schema]"
            "(https://pink-project.github.io/PINK-annotation-schema/widoco/index-en.html)."
            "A *descriptor* or *indicator* is a property that provides information about "
            "the state of a system. It simplifies complex realities into measurable values "
            "that can guide decisions."
            "\n\n"
            "A service for browsing and searching CHEMINF can be found "
            "[here](https://ontobee.org/ontology/CHEMINF?iri=http://semanticscience.org/resource/CHEMINF_000123)."
        ),
        lang="en",
    ),
}

# Mapped terms that we want to add
mapped_terms = [
    # Classes
    "cheminf:CHEMINF_000000",  # chemical entity
    "cheminf:CHEMINF_000266",  # chemical substance
    "obo:CHEBI_23367",  # molecular entity
    "obo:CHEBI_33250",  # atom
    "obo:CHEBI_36357",  # polyatomic entity

    # Properties
    "obo:IAO_0000136",  # is about
    "obo:RO_0000056",  # participates in
    "cheminf:CHEMINF_000012",  # has value
]

# Terms we don't want to add to the PINK Annotation Schema
ignored_terms = [
    ":CHEMINF_000017",  # information about a chemical entity
    ":CHEMINF_000047",  # conforms to
    ":CHEMINF_000063",  # chemical bond
    ":CHEMINF_000143",  # is descriptor of
    ":CHEMINF_000198",  #
    ":CHEMINF_000238",  # meltability
    ":CHEMINF_000305",  #
    ":CHEMINF_000308",  #
    ":CHEMINF_000309",  #
    ":CHEMINF_000310",  #
    ":CHEMINF_000311",  #
    ":CHEMINF_000314",  #
    ":CHEMINF_000317",  #
    ":CHEMINF_000319",  #
    ":CHEMINF_000324",  #
    ":CHEMINF_000334",  #
    ":CHEMINF_000335",  #
    ":CHEMINF_000336",  #
    ":CHEMINF_000337",  #
    ":CHEMINF_000338",  #
    ":CHEMINF_000345",  #
    ":CHEMINF_000346",  #
    ":CHEMINF_000354",  # execution of ACD/Labs PhysChem software library version 12.01
    ":CHEMINF_000369",  #
    ":CHEMINF_000370",  #
    ":CHEMINF_000371",  #
    ":CHEMINF_000372",  #
    ":CHEMINF_000373",  #
    ":CHEMINF_000374",  #
    ":CHEMINF_000375",  #
    ":CHEMINF_000376",  #
    ":CHEMINF_000379",  #
    ":CHEMINF_000382",  #
    ":CHEMINF_000387",  #
    ":CHEMINF_000388",  #
    ":CHEMINF_000389",  #
    ":CHEMINF_000390",  #
    ":CHEMINF_000391",  #
    ":CHEMINF_000392",  #
    ":CHEMINF_000395",  #
    ":CHEMINF_000396",  #
    ":CHEMINF_000399",  #
    ":CHEMINF_000469",  # CRID validation
    ":CHEMINF_000511",  #
    ":CHEMINF_000512",  #
    ":CHEMINF_000802",  #
    ":CHEMINF_000803",  #
    ":CHEMINF_000804",  #
    ":CHEMINF_000805",  #
    ":CHEMINF_000806",  #
    ":CHEMINF_000807",  #
    ":CHEMINF_000808",  #
    "obo:BFO_0000002",  # continuant
    "obo:BFO_0000003",  # occurant
    "obo:BFO_0000020",  # specifically dependent continuant
    "obo:BFO_0000040",  # material entity
    "obo:IAO_0000027",  #
    "obo:IAO_0000030",  #
    "obo:IAO_0000310",  #
    "obo:IAO_0000403",  #
    "obo:IAO_0000577",  #
    "semonto:is_output_of",  # is output of
]


rootdir = Path(__file__).resolve().parent.parent

# Load local squashed cheminf
ts1 = Triplestore(backend="rdflib")
ts1.parse(rootdir / "sources" / "cheminf.ttl")
CHEMINF = ts1.namespaces["cheminf"]
query = f"""
PREFIX rdfs: <{RDFS}>
PREFIX cheminf: <{CHEMINF}>
SELECT ?iri WHERE {{
  ?iri rdfs:subClassOf* cheminf:CHEMINF_000123 .
}}
"""
r = ts1.query(query)
iris = [t[0] for t in r]


def get_concept(ts, iri):
    """Return a list of triples describing the IRI."""
    iri = ts.expand_iri(iri)
    query = f"""
    PREFIX rdfs: <{RDFS}>
    PREFIX owl: <{OWL}>
    PREFIX cheminf: <{CHEMINF}>
    CONSTRUCT {{
      <{iri}> ?p ?o .
      ?rs ?rp ?ro .
    }} WHERE {{
      {{
        <{iri}> ?p ?o .
      }} UNION {{
        <{iri}> rdfs:subClassOf ?rs .
        ?rs a owl:Restriction ;
           ?rp ?ro .
      }}
    }}
    """
    return ts.query(query)


# Create new triplestore
ts = Triplestore(backend="rdflib")
ts.bind("", "http://semanticscience.org/resource/")
ts.bind("widoco", "https://w3id.org/widoco/vocab#")
for prefix, ns in ts1.namespaces.items():
    if prefix not in ts.namespaces and ns not in ts.namespaces.values():
        ts.bind(prefix, ns)

for iri in iris:
    print(iriname(iri))
    ts.add_triples(get_concept(ts1, iri))

# Add mapped terms
for term in mapped_terms:
    ts.add_triples(get_concept(ts1, term))

# Remove all references to ignored terms
print()
print("Remove:")
for term in ignored_terms:
    iri = ts.expand_iri(term)
    print("  -", iri)

    ts.update(
        f"""
        PREFIX rdfs: <{RDFS}>
        PREFIX owl: <{OWL}>
        DELETE {{
          ?iri rdfs:subClassOf ?s .
          ?s ?pred <{iri}> .
          ?s ?p ?o .
        }} WHERE {{
          ?iri rdfs:subClassOf ?s .
          ?s a owl:Restriction .
          ?s ?pred <{iri}> .
          ?s ?p ?o .
        }}
        """
    )

    ts.update(
        f"""DELETE WHERE {{
          ?s owl:equivalentClass ?b .
          ?b a owl:Class .
          ?b owl:intersectionOf ( <{iri}> ?other ) .
        }}"""
    )
    ts.remove(CHEMINF.CHEMINF_000044, OWL.equivalentClass)
    ts.remove(CHEMINF.CHEMINF_000511, OWL.equivalentClass)
    ts.remove(CHEMINF.CHEMINF_000512, OWL.equivalentClass)
    ts.remove(CHEMINF.CHEMINF_000513, OWL.equivalentClass)
    ts.remove(object=iri)
    #ts.remove(predicate=iri)
    #ts.remove(subject=iri)

# Add ontology to triplestore
triples = [(ontology_iri, RDF.type, OWL.Ontology)]
for p, o in ontology_descr.items():
    triples.append((ontology_iri, p, o))
ts.add_triples(triples)

# Write cheminf.ttl
ttl = ts.serialize(format="turtle")
with open(rootdir / "cheminf.ttl", "wt") as f:
    f.write("# This file is generated/rewritten by scripts/cheminf-extract.py\n")
    f.write(ttl)

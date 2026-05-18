"""Script that generates a JSON-LD context for a knowledge base.

The knowledge base must have a SPARQL endpoint supported by Tripper
(typically via the sparqlwrapper plugin).

Before running this script, you must create a session configuration
file named `session_conf.yaml` in the root directory.
This file should have the following content:

    PINKKB:
      backend: sparqlwrapper
      base_iri: https://graphdb.pink-project.eu/repositories/testing
      update_iri: https://graphdb.pink-project.eu/repositories/testing/statements
      check_url: https://graphdb.pink-project.eu/repositories
      username: jesper-friis
      password: KEYRING

    MemDB:
      backend: rdflib

Please replace the PINKKB username `jesper-friis` with your username.

Set the password by running

    keyring set PINKKB <my_password>

See https://emmc-asbl.github.io/tripper/latest/session/ for details.

"""
import json
from pathlib import Path

from tripper import RDF, RDFS, SKOS, Session, Triplestore
from tripper.utils import prefix_iri


rootdir = Path(__file__).resolve().parent.parent
outdir = rootdir / "jsonld"
outfile = outdir / "pinkkb.json"
conffile = rootdir / "session_conf.yaml"

# PINKKB doesn't contain the SSbD Core Ontology yet, so we can't test.
# For now we therefore use MemDB and populate it manyally with SSbD core.
#session_name = "PINKKB"
session_name = "MemDB"  # to be replaced with PINKKB

session = Session(conffile)
ts = session.get_triplestore(session_name)

# Populate MemDB manually
if session_name == "MemDB":
    ts.parse("https://w3id.org/ssbd")

# Define prefixes
ts.bind("bibo", "http://purl.org/ontology/bibo/")
ts.bind("chemowl", "http://www.semanticweb.org/ontologies/cheminf.owl#")
ts.bind("dcat", "http://www.w3.org/ns/dcat#")
ts.bind("dcatap", "http://data.europa.eu/r5r/")
ts.bind("dcterms", "http://purl.org/dc/terms/")
ts.bind("ddoc", "https://w3id.org/emmo/application/datadoc#")
ts.bind("foaf", "http://xmlns.com/foaf/0.1/")
ts.bind("obo", "http://purl.obolibrary.org/obo/")
ts.bind("oboowl", "http://www.geneontology.org/formats/oboInOwl#")
ts.bind("owl", "http://www.w3.org/2002/07/owl#")
ts.bind("prov", "http://www.w3.org/ns/prov#")
ts.bind("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
ts.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
ts.bind("skos", "http://www.w3.org/2004/02/skos/core#")
ts.bind("ssbd", "https://w3id.org/ssbd/")
ts.bind("swrl", "http://www.w3.org/2003/11/swrl#")
ts.bind("vann", "http://purl.org/vocab/vann/")
ts.bind("widoco", "https://w3id.org/widoco/vocab#")
ts.bind("xsd", "http://www.w3.org/2001/XMLSchema#")


# Help functions

def add(ctx, triples, prefixes, type=None):
    """Add `triples` to the context `ctx`."""
    labels = {s: str(o) for s, p, o in triples if p == SKOS.prefLabel}
    ranges = {s: o for s, p, o in triples if p == RDFS.range}
    for iri, label in labels.items():
        ctx[label] = {
            "@id": prefix_iri(iri, prefixes),
            "@type": type if type else prefix_iri(ranges[iri], prefixes),
        }


def get_query(target, prefixes, isprop=True):
    """Return SPARQL query for given target.

    `target` should be one of:
      - "owl:AnnotationProperty"
      - "owl:ObjectProperty"
      - "owl:DatatypeProperty"
      - "owl:Class"
    """
    pf = [f"PREFIX {prefix}: <{ns}>" for prefix, ns in prefixes.items()]
    range = "?prop rdfs:range ?range ." if isprop else ""
    return "\n".join(pf) + "\n" + f"""
CONSTRUCT {{
  ?prop a {target} ;
    skos:prefLabel ?label .
  {range}
}}
WHERE {{
  ?prop a {target} .
  {range}
  OPTIONAL {{
    {{
      ?prop skos:prefLabel ?label
    }} UNION {{
      ?prop rdfs:label ?label
    }} .
  }}
}}
"""


# Prepare the context
ctx = {"@version": 1.1}  # Inner context
context = {"@context": ctx}  # Full context

# Add prefixes to context
prefixes = {prefix: str(ns) for prefix, ns in ts.namespaces.items()}
for prefix in sorted(prefixes):
    ctx[prefix] = prefixes[prefix]

# Populate the context
q1 = get_query("owl:AnnotationProperty", prefixes)
q2 = get_query("owl:ObjectProperty", prefixes)
q3 = get_query("owl:DatatypeProperty", prefixes)
q4 = get_query("owl:Class", prefixes, isprop=False)
r1 = list(ts.query(q1))
r2 = list(ts.query(q2))
r3 = list(ts.query(q3))
r4 = list(ts.query(q4))
add(ctx, r1, prefixes)
add(ctx, r2, prefixes, "@id")
add(ctx, r3, prefixes)
add(ctx, r4, prefixes, "owl:Class")

# Write context to file
outdir.mkdir(exist_ok=True)
with open(outfile, "wt", encoding="utf-8") as f:
    json.dump(context, f, indent=2)

print(outfile.read_text())

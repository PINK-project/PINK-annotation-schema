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

from tripper import OWL, RDF, RDFS, SKOS, Session, Triplestore
from tripper.utils import prefix_iri
from tripper.datadoc.utils import iriname


rootdir = Path(__file__).resolve().parent.parent
outdir = rootdir / "jsonld"
outfile = outdir / "pinkkb.json"
conffile = rootdir / "session_conf.yaml"

# PINKKB doesn't contain the SSbD Core Ontology yet, so we can't test.
# For now we therefore use MemDB and populate it manually with SSbD core.
#session_name = "PINKKB"
session_name = "MemDB"  # to be replaced with PINKKB

session = Session(conffile)
ts = session.get_triplestore(session_name)

# Populate MemDB manually
if session_name == "MemDB":
    ts.parse("https://w3id.org/ssbd")

# Define prefixes
prefixes = {
    "bibo": "http://purl.org/ontology/bibo/",
    "cheminf": "http://semanticscience.org/resource/",
    "chemowl": "http://www.semanticweb.org/ontologies/cheminf.owl#",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dcatap": "http://data.europa.eu/r5r/",
    "dcterms": "http://purl.org/dc/terms/",
    "ddoc": "https://w3id.org/emmo/application/datadoc#",
    "dm": "https://w3id.org/emmo/domain/datamodel#",
    "emmo": "https://w3id.org/emmo/hume#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "obo": "http://purl.obolibrary.org/obo/",
    "oboowl": "http://www.geneontology.org/formats/oboInOwl#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "prov": "http://www.w3.org/ns/prov#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "ssbd": "https://w3id.org/ssbd/",
    "swrl": "http://www.w3.org/2003/11/swrl#",
    "vann": "http://purl.org/vocab/vann/",
    "widoco": "https://w3id.org/widoco/vocab#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}
for prefix, ns in prefixes.items():
    ts.bind(prefix, ns)

# Prepare the context
ctx = {"@version": 1.1}  # Inner context
context = {"@context": ctx}  # Full context

# Add prefixes to context
for prefix in sorted(prefixes):
    ctx[prefix] = prefixes[prefix]


# Execute SPARQL query + workaround bug that None is returned as "None"
q = """
SELECT ?iri ?prefLabel ?type ?range
WHERE {
  ?iri a ?type .
  OPTIONAL { ?iri rdfs:range ?range } .
  OPTIONAL { ?iri skos:prefLabel ?prefLabel } .
  VALUES ?type { owl:AnnotationProperty owl:ObjectProperty owl:DatatypeProperty owl:Class }
}
"""
r = [[x if x and x != "None" else None for x in t] for t in ts.query(q)]

prefixed = {iri: prefix_iri(iri, prefixes) for iri, _, _, _ in r}
keys = {}
used_keys = {}

for iri, prefLabel, _, _ in r:
    if prefLabel:
        key = str(prefLabel)
    else:
        name = iriname(iri)
        key = prefixed[iri] if name in used_keys else name

    if key in used_keys:
        raise ValueError(f"Duplicate context key {key!r}: {used_keys[key]} and {iri}")

    keys[iri] = key
    used_keys[key] = iri
ranges = {iri: prefix_iri(range, prefixes) for iri, _, _, range in r if range}
results = [  # New sorted result list
    (keys[iri], iri, type)
    for iri, _, type, _ in sorted(r, key=lambda x: keys[x[0]])
]

# Add annotation properties to context
for key, iri, type in results:
    if type == OWL.AnnotationProperty:
        pf = prefixed[iri]
        ctx[key] = {"@id": pf, "@type": ranges[iri]} if iri in ranges else pf

# Add object properties to context
for key, iri, type in results:
    if type == OWL.ObjectProperty:
        ctx[key] = {"@id": prefixed[iri], "@type": "@id"}

# Add data properties to context
for key, iri, type in results:
    if type == OWL.DatatypeProperty:
        pf = prefixed[iri]
        ctx[key] = {"@id": pf, "@type": ranges[iri]} if iri in ranges else pf

# Add classes to context
for key, iri, type in results:
    if type == OWL.Class:
        ctx[keys[iri]] = {"@id": prefixed[iri], "@type": "owl:Class"}

# Write context to file
outdir.mkdir(exist_ok=True)
with open(outfile, "wt", encoding="utf-8") as f:
    json.dump(context, f, indent=2)

#print(outfile.read_text())

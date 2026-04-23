"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documentation.
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd
from ontopy import get_ontology
from tripper import Triplestore
from tripper.datadoc import (
    get_context,
    get_keywords,
)
from tripper.datadoc.tabledoc import TableDoc

sys.path.append(str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
from validation.validate import load_shapes, shacl_validate

from parseutils import (
    correct_pink_dataframes,
    PREFIXES,
    list_columns,
    property_iri_dict
)

# import the pink ontology for accessing labels and
# convert to IRIs (just before storing into the triplestore)
onto = get_ontology("https://ssbd-ontology.github.io/core/core-inferred.ttl").load()

ts = Triplestore('rdflib')

AGENTS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&"
    "gid=1445327120"
)
agents = pd.read_csv(AGENTS_URL)

# Get pink keywords
#kw = get_keywords(theme=None)
#kw.load_yaml(
#    "https://raw.githubusercontent.com/ssbd-ontology/core/refs/"
#    "heads/gh-pages/context/keywords.yaml",
#    redefine="allow",
#)

context = get_context(
    "https://w3id.org/ssbd/context/", theme=None
)

# Agents
print("PREPARING AGENT DOCUMENTATION")
agents["@type"] = [["prov:Agent"]] * len(agents)
agents = agents.drop(columns=["e-mail", "affiliation.name", "affiliation.id"])
#agents = agents[~agents["identifier"].isin(ts.subjects())]

agents_corrected = correct_pink_dataframes(agents, onto)
agents_corrected.to_csv("agents_clean.csv", index=False)
agentdocumentation = TableDoc.parse_csv(
    "agents_clean.csv",
    #keywords=kw,
    context=context,
    prefixes=PREFIXES,
)



ad = agentdocumentation.save(ts)

# Get absolute current path
root_path = Path(__file__).parent.parent.resolve()
validation_path = root_path / "validation"
shacl_graph = load_shapes("https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/gh-pages/shacl/shapes.ttl")
shacl_graph.parse("https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/gh-pages/shacl/shapes-ssbd.ttl", format="turtle")


conforms, results_graph, report = shacl_validate(
    data_graph=ts.backend.graph,
    shacl_graph=shacl_graph,
    inference="rdfs",
    abort_on_first=False,
)


if not conforms:
    print("Validation failed.")
    print(report)

if conforms:
    print("Validation passed")
    print("unfortunately direct pushing is no longer possible")
    print("making a jsonld from my graph")
    ts.serialize("pink-agents.ttl", format="turtle")
    
    graph = dict()

    graph['@context'] = ad['@context']
    graph['@graph'] = ad['@graph']

    # Store the jsonlds for joh
    with open('jsonld/pink-agents.jsonld', 'wt') as f: 
        json.dump(graph, f, indent=2)




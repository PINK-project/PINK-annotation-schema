"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documenting the PINK agents.
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

from pink.parseutils import (
    PREFIXES,
)

ts = Triplestore('rdflib')


context = get_context(
    "https://w3id.org/ssbd/context/", theme=None
)

# Agents
agentdocumentation = TableDoc.parse_csv(
    "agents.csv",
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
    ts.serialize("agents.ttl", format="turtle")
    
    graph = dict()

    graph['@context'] = ad['@context']
    graph['@graph'] = ad['@graph']

    # Store the jsonlds for joh
    with open('agents.jsonld', 'wt') as f: 
        json.dump(graph, f, indent=2)




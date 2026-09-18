"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documentation.

This script reads the cleaned csv files from the previous step 
and converts them to RDF triples using the TableDoc class 
from the tripper library. 
It then validates the generated RDF against SHACL shapes and 
saves the valid triples to a jsonlid file for later upload to the PINK KB.
"""

import json
import sys
from pathlib import Path

from tripper import Triplestore
from tripper.datadoc import get_context, store
from tripper.datadoc.tabledoc import TableDoc
from pink.parseutils import (
    PREFIXES as prefixes,
)
from pink.pinkkb import pinkkb_classes

sys.path.append(str(Path(__file__).resolve().parents[1]))
# pylint: disable=wrong-import-position,import-error
from validation.validate import load_shapes, shacl_validate


# SSbD core context
context = get_context(
    "https://w3id.org/ssbd/context/", theme=None
)

# Add classes that alreadt exist in the PINKKB
classes = pinkkb_classes()

context.add_context(classes)


# Parse the tables.
datasettypedocumentation = TableDoc.parse_csv(
    "datasettypes_clean.csv",
    context=context,
    prefixes=prefixes,
)

swdocumentation = TableDoc.parse_csv(
    "sw_clean.csv",
    context=context,
    prefixes=prefixes,
)


compdocumentation = TableDoc.parse_csv(
    "comp_clean.csv", 
    context=context, 
    prefixes=prefixes
)

# Put all created resources into a list of dicts
resources = datasettypedocumentation.asdicts() + swdocumentation.asdicts() +  compdocumentation.asdicts()

# Create the local triplestore to make the graph
ts = Triplestore("rdflib")

# Store in the graph
jsonld = store(ts, resources, context=context, prefixes=prefixes)


# Get absolute current path to get the validation tool 
# This will change once the validation is made available
# as a package
root_path = Path(__file__).parent.parent.resolve()
validation_path = root_path / "validation"

# Get shacl shapes the ssbd core ontology
shacl_graph = load_shapes("https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/gh-pages/shacl/shapes.ttl")
shacl_graph.parse("https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/gh-pages/shacl/shapes-ssbd.ttl", format="turtle")


# Check validity of graph 
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
    print("Direct pushing is not possible")
    print("making a jsonld from my graph")
    ts.serialize("googlespreadsheet_resources.ttl", format="turtle")
    

    # Store the jsonlds for joh
    with open('pink_googlespreadsheet_resources.jsonld', 'wt') as f: 
        json.dump(jsonld, f, indent=2)


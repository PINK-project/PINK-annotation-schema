"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documentation.
"""

import json
import re
import sys
from pathlib import Path

import dateutil
import pandas as pd
from ontopy import get_ontology
from ontopy.exceptions import NoSuchLabelError
from tripper import Triplestore
from tripper.datadoc import (
    get_context,
    get_keywords,
    told,
)
from tripper.datadoc.tabledoc import TableDoc

sys.path.append(str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
from validation.validate import load_shapes, shacl_validate

# Get pink keywords
kw = get_keywords(theme=None)
kw.load_yaml(
    "https://pink-project.github.io/PINK-annotation-schema/"
    "context/keywords.yaml",
    redefine="allow",
)

context = get_context(
    "https://pink-project.github.io/PINK-annotation-schema/"
    "context/pink_annotation_schema.jsonld"
)

# Choice of prefixes
prefixes = {
    "mw": "https://modelwave.it/ontology/",
    "rights": "http://publications.europa.eu/resource/authority/access-right/",
    "datasettype": "https://w3id.org/pink/datasettype/",
    "qsar": "https://w3id.org/pink/qsar/",
}


# import the pink ontology for accessing labels and
# convert to IRIs (just before storing into the triplestore)
onto = get_ontology("pink_annotation_schema.ttl").load()

# create the triplestore
ts = Triplestore("rdflib")
# Add the reasoned ontology to the triplestore
ts.parse(
    "https://raw.githubusercontent.com/PINK-project/PINK-annotation-schema/"
    "refs/heads/gh-pages/pink_annotation_schema-inferred.ttl"
)

# Get absolute current path
root_path = Path(__file__).parent.parent.resolve()

ex_ind_path = root_path / "csv_files" / "ex_ind.csv"
example_ind = TableDoc.parse_csv(
    ex_ind_path,
    keywords=kw,
    context=context,
    prefixes=prefixes,
)

example_ind.save(ts)

ex_class_path = root_path / "csv_files" / "ex_class.csv"
example_class = TableDoc.parse_csv(
    ex_class_path,
    keywords=kw,
    context=context,
    prefixes=prefixes,
)

example_class.save(ts)


# Get absolute current path
validation_path = root_path / "validation"
shacl_graph = load_shapes(validation_path / "shapes.ttl")
shacl_graph.parse(validation_path / "shapes-pink.ttl", format="turtle")


conforms, results_graph, report = shacl_validate(
    data_graph=ts.backend.graph,
    shacl_graph=shacl_graph,
    inference="rdfs",
    abort_on_first=False,
)

if not conforms:
    print("Validation failed.")
    print(report)

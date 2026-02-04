#!/usr/bin/env python
# Generates context/generated_keywords.yml and context/pink_context.json

from pathlib import Path

from tripper import Triplestore
from tripper.datadoc import get_keywords
import logging

# Note that logging to screen is not always happening
logging.getLogger().setLevel(logging.INFO)


thisdir = Path(__file__).resolve().parent
rootdir = thisdir.parent

ts =  Triplestore("rdflib")

ts.parse(rootdir / "pink_annotation_schema.ttl")

kw = get_keywords()

kw.add_prefix("pink", "https://w3id.org/pink#")
kw.data.prefixes["emmo"] = "https://w3id.org/emmo/hume#"

kw.load_rdf(ts, redefine="allow")

kw.save_yaml(rootdir / "context/generated_keywords.yml")

kw.save_context(rootdir / "context/pink_context.json")

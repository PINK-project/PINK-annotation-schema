"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documentation.
"""

import json
import sys
from pathlib import Path

from tripper import Triplestore
from tripper.datadoc import (
    get_context,
    get_keywords,)

from tripper.datadoc.tabledoc import TableDoc

sys.path.append(str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
from validation.validate import load_shapes, shacl_validate

from parseutils import (
    PREFIXES as prefixes,
)

kw = get_keywords(theme=None)
kw.load_yaml(
    "https://raw.githubusercontent.com/ssbd-ontology/core/refs/"
    "heads/gh-pages/context/keywords.yaml",
    redefine="allow",
)


context = get_context(
    "https://w3id.org/ssbd/context/", theme=None
)



swdocumentation = TableDoc.parse_csv(
    "sw_clean.csv",
    keywords=kw,
    context=context,
    # baseiri='https://w3id.org/pink/',
    prefixes=prefixes,
)


compdocumentation = TableDoc.parse_csv(
    "comp_clean.csv", 
    keywords=kw, 
    context=context, 
    prefixes=prefixes
)

datasettypedocumentation = TableDoc.parse_csv(
    "datasettypes_clean.csv",
    keywords=kw,
    context=context,
    prefixes=prefixes,
)

# Save the data to the triplstore
# create the triplestore
ts = Triplestore("rdflib")



dd = datasettypedocumentation.save(ts)
sd = swdocumentation.save(ts)
cd = compdocumentation.save(ts)


####
#dmtable = DMTable.from_csv("datamodels.csv")


####


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
    ts.serialize("everything.ttl", format="turtle")
    
    graph = dict()

    graph['@context'] = sd['@context']
    graph['@graph'] =sd['@graph'] + cd['@graph'] + dd['@graph']

    # Store the jsonlds for joh
    with open('jsonld/pink_googlespreadsheet_resources.jsonld', 'wt') as f: 
        json.dump(graph, f, indent=2)



    # Connect to PINK KB
    #username = keyring.get_password("PINK_graphdb", "username")
    #password = keyring.get_password("PINK_graphdb", "password")

    #kb = Triplestore(
    #    backend="sparqlwrapper", 
    #    base_iri="https://graphdb.pink-project.eu/repositories/testing", 
    #    username=username, 
    #    password=password, 
    #    update_iri="https://graphdb.pink-project.eu/repositories/testing/statements",
    #    )
    #for s, p, o in ts.triples():
    #    kb.add((s, p, o))

    #print(search(kb))



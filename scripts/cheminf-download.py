# Script that downloads  CHEMINF and save it to sources/cheminf.ttl

from pathlib import Path

import yaml
from ontopy import get_ontology


rootdir = Path(__file__).resolve().parent.parent
outdir = rootdir / "sources"
outdir.mkdir(exist_ok=True)
endpoint = (
    "https://raw.githubusercontent.com/semanticchemistry/"
    "semanticchemistry/master/ontology/cheminf.owl"
)

onto = get_ontology(endpoint).load()

onto.save(
    outdir / "cheminf.ttl",
    squash=True,
    namespaces={
        "obo": "http://purl.obolibrary.org/obo/",
        "cheminf": "http://semanticscience.org/resource/",
        "semonto": "http://www.semanticweb.org/ontologies/",
        # The following namespaces are really messy...
        "chemowl": "http://www.semanticweb.org/ontologies/cheminf.owl#",
        "oboowl": "http://www.geneontology.org/formats/oboInOwl#",
        "skosref": "https://www.w3.org/2009/08/skos-reference/skos.html#",
        "chemcore": "http://semanticscience.org/ontology/cheminf-core.owl#",
        "ro": "http://www.obofoundry.org/ro/ro.owl#",
        "dct": "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/",
    },
)

if False:
    d = {}
    chemical_descriptor = onto.CHEMINF_000123
    for c in chemical_descriptor.descendants():
        label = str(c.label.first())
        descr = str((c.description if c.description else c.comment).first())
        d[c.name] = {"label": label, "description": descr}

    with open(outdir / "cheminf-extract.yaml", "wt") as f:
        f.write("# Generated with scripts/cheminf-download.py\n")
        yaml.dump(d, f, sort_keys=False)

# PINK Annotation Schema

This repository shows how the SSbD Core ontology is used to document resources within the PINK project,
including practical examples, and provides the tools used to turn the PINK documentation spreadsheets
into a graph that can be uploaded to the PINK knowledge base (PINK KB).

In the SSbD Core ontology repository, [a general introduction](https://ssbd-ontology.github.io/core/docs/document-your-data.html)
to documenting resources is provided.
This includes the [expected annotations](https://ssbd-ontology.github.io/core/docs/document-your-data.html#expected-minimum-annotations-by-resource-type),
chosen within the PINK project. Please refer to that documentation for guidance.

## Contents

- [Annotating resources](annotating.md) - project-wide resources and example spreadsheets
- [Scripts](scripts.md) - preparing and validating the documentation tables, generating the graph,
  and other helper scripts

```{toctree}
:hidden:

annotating
scripts
```

## Installation

Users are expected to be familiar with Python (and Python environments).
Install the Python dependencies and the PINK utility functions with

```bash
pip install -r requirements.txt
pip install .
```

## Typical workflow

To generate and validate all documentation:

1. **Prepare data:** Run `prepare-tables <Google spreadsheet ID>` to download, prepare and validate the tables, and correct the spreadsheet based on the logs
2. **Convert to RDF:** Run `generate-graph` on the clean tables to convert them to validated RDF triples
3. **Parse datamodels:** Run `step3_dmtable_parse.py` to convert datamodels to RDF format
4. **Query results:** Use `search_pink_kb.py` to verify and search the generated knowledge base

See [Scripts](scripts.md) for the details of each step.

## Legacy

The PINK Annotation Schema has been renamed and is now maintained as the SSbD Core Ontology.

- Official documentation: <https://ssbd-ontology.github.io/core/>
- GitHub repository: <https://github.com/ssbd-ontology/core>

For ontology development, authoritative classes/properties, and ongoing updates, use the SSbD Core Ontology repository.

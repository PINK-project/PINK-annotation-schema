# PINK Annotation Schema

This repository shows how the SSbD Core ontology is used to document resources within the PINK project,
including practical examples, and provides the tools used to turn the PINK documentation spreadsheets
into a graph that can be uploaded to the PINK knowledge base.

**Documentation: <https://pink-project.github.io/PINK-annotation-schema/>**

- [Annotating resources](https://pink-project.github.io/PINK-annotation-schema/annotating.html) - project-wide resources and example spreadsheets
- [Validation profiles](https://pink-project.github.io/PINK-annotation-schema/profiles.html) - what is expected for each type of resource, and how it is validated
- [Scripts](https://pink-project.github.io/PINK-annotation-schema/scripts.html) - preparing and validating the documentation tables, and generating the graph

## Quick start

```bash
pip install -r requirements.txt
pip install .
prepare-tables <Google spreadsheet ID>
generate-graph datasettypes_clean.csv sw_clean.csv comp_clean.csv -o graph.ttl
```

## Editing the documentation

The documentation is written in Markdown in [`docs/`](docs/) and published to GitHub Pages
on every push to `main`. To preview it locally:

```bash
pip install -r docs/requirements.txt
sphinx-build -b html docs public   # then open public/index.html
```

## Legacy

The PINK Annotation Schema has been renamed and is now maintained as the SSbD Core Ontology:
<https://ssbd-ontology.github.io/core/> ([GitHub](https://github.com/ssbd-ontology/core)).

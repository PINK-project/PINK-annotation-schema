# Annotating resources

## Project-wide resources

Some resources are project-wide. One example is the agents, i.e. the people and organisations that
prepare and own data etc. These are contained in the file
[`project_wide_resources/agents.csv`](https://github.com/PINK-project/PINK-annotation-schema/blob/main/project_wide_resources/agents.csv).
Please update this file as needed.

## Example spreadsheets (CSV)

The files in `example_spreadsheets/` provide compact examples that can be used as templates when annotating resources.
When populated correctly, it should be possible to parse them directly with tripper:

- [software_release_example.csv](../example_spreadsheets/software_release_example.csv)
- [computation_type_example.csv](../example_spreadsheets/computation_type_example.csv)
- [dataset_type_example.csv](../example_spreadsheets/dataset_type_example.csv)

Notes:

- Multi-valued properties from the source sheets (for example repeated `keyword`, `chemicalClass`, `hasInput`, `hasOutput`, `subClassOf`)
  are represented as semicolon-separated values in a single column in these examples.
- When documenting computation types, it is expected that you state which SSbD assessments (see the SSbD Core Ontology) they are subclasses of.

## Generating RDF from a spreadsheet with datadoc

Tripper provides a tool called `datadoc` to populate a triplestore.
While it currently cannot be used directly with the PINK KB, it can be used to generate an RDF
representation, serialised in Turtle, that can be uploaded to the PINK KB.

Provided that the requirements in `requirements.txt` are installed, this can be done with

```bash
datadoc add software_release_example.csv --context=https://w3id.org/ssbd/context/ --dump=kb.ttl
```

Similarly, the other example spreadsheets can be added to generate their RDF representations:

```bash
datadoc add computation_type_example.csv --context=https://w3id.org/ssbd/context/ --dump=kb_computation.ttl
datadoc add dataset_type_example.csv --context=https://w3id.org/ssbd/context/ --dump=kb_dataset.ttl
```

For the PINK documentation spreadsheets, use the [scripts](scripts.md) instead.

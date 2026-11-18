# PINK Annotation Schema

This repository is intended for usage of the SSBD ontology to document resources within in the PINK project,
including practical examples.
For the legacy content see below.

In the SSbD Core ontology repository, [a general introduction](https://ssbd-ontology.github.io/core/docs/document-your-data.html) to documenting resources is provided.
This includes the [expected annotations](https://ssbd-ontology.github.io/core/docs/document-your-data.html#expected-minimum-annotations-by-resource-type),
chosen within the PINK project. Please refer to that documentation for guidance.


This repository contains some utility functions that need to be installed. You can do this with
```bash
pip install .
```
Users are expected to be familiar with python (and python environments)

## Project-wide resources

Some resources are projectwide. One example are the agents, i.e. people and organisations that
prepare and own data etc. These are contained in the script file
`project_wide_resources/agents.csv`. Please update this file as needed.

## Example Spreadsheets (CSV)

The files in `example_spreadsheets/` provide compact examples that can be used as templates when annotating resources.
When populated correctly, it should be possible to parse them directly with tripper:

- [software_release_example.csv](example_spreadsheets/software_release_example.csv)
- [computation_type_example.csv](example_spreadsheets/computation_type_example.csv)
- [dataset_type_example.csv](example_spreadsheets/dataset_type_example.csv)

Notes:
- Multi-valued properties from the source sheets (for example repeated `keyword`, `chemicalClass`, `hasInput`, `hasOutput`, `subClassOf`) are represented as semicolon-separated values in a single column in these examples.
- When documenting computation types, it is expected that which SSbD Assessemnts (check SSbD Core Ontology) they are subclasses of.

Tripper provides a nice tool to populate a triplestore called 'datadoc'.
While it is not possible to se this directly with the PINK KB, currently, it is nice to
use it to generate a rdf-representation, serialised in turtle that can be uploaded to the PINK KB.

This can be done with `datadoc add software_release_example.csv --context=https://w3id.org/ssbd/context/ --dump=kb.ttl`
provided that the reqriements described in `requirements.txt` are installed.

Similarly, other example spreadsheets can be added to generate their RDF representations:
```
datadoc add computation_type_example.csv --context=https://w3id.org/ssbd/context/ --dump=kb_computation.ttl
datadoc add dataset_type_example.csv --context=https://w3id.org/ssbd/context/ --dump=kb_dataset.ttl
```


## Examples of scripts used for parsing documentation tables

These are scripts used to parse and process the Google Spreadsheets used as initial documentation tables for the PINK project.

In order to run scripts in the current repository a working python environment is required.
Please install the python dependencies defined in `requirements.txt` with e.g.

```bash
pip install -r requirements.txt
```

A few utility functions for PINK are also made available and ned to be installed with

```bash
pip install .
```



This repository contains several scripts for generating and parsing resources documented in the
Google Spreadsheets within the PINK project. Below is a description of each script and how to use them:

### 1. Prepare and validate the documentation tables

**Purpose:** Reads the documentation spreadsheet, prepares tables that can be parsed directly
by `tripper` (and `dlite` for the datamodels), and validates them.

**Usage:**
```bash
prepare-tables SOURCE [--type TYPE] [--sheet NAME] [-o FOLDER] [-c CREDENTIALS]
```
`SOURCE` is the ID of a Google spreadsheet (e.g. `1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU`
for the PINK KB resources), an Excel file (`.xlsx`) or a CSV file.

In a Google spreadsheet or Excel file, the tabs are recognised by their name:

| Tab name         | Type          | Prepared tables                                  |
|------------------|---------------|--------------------------------------------------|
| `Software...`    | `software`    | `sw_clean.csv` and `comp_clean.csv` (computations from the software tab) |
| `Computation...` | `computation` | `computations_clean.csv`                         |
| `Dataset Type`   | `datasettype` | `datasettypes_clean.csv` and `datamodels.csv`    |
| `Dataset`        | `dataset`     | `datasets_clean.csv`                             |

All recognised tabs are prepared, or only the one given with `--type`.
Another tab can be chosen with `--sheet`. For such a tab, and for a CSV file, the type is
given with `--type` or asked for.
Cells are read as the text shown in the spreadsheet (e.g. a version written as `January 2015`).

**What it does:**
- Prepares the tables: translates the column names to tripper keywords (using the term
  definitions), splits lists, adds prefixes and looks up ontology terms by their label.
  Columns with `(comment)` in their name are left out.
- Splits the software tab into a software table and a computation table.
  The label, description and curator of a computation are made from its software row.
- Validates each table against its profile in `profiles/`, which defines the expected
  properties, their datatypes and whether they are mandatory, recommended, conditional or
  optional. Possible datatypes are:
  - string
  - IRI
  - URL (resolvable IRI; a URL that needs a login gives a warning)
  - boolean
  - dateTime
  - SSbDCore (entry exists in the SSbD Core ontology)
  - AgentIRI (ROR or ORCID identifier)
  - PersonIRI (ORCID identifier)
  - MediaTypeIRI (IANA media type, e.g. `iana:application/zip`)
- Wrong prefixes are not corrected, but reported (with a hint if the term exists with another prefix).
  Columns that are not tripper keywords are reported as errors.
- ORCIDs are looked up anonymously, unless a credentials file is given with `-c`
  (default `credentials.json`, if it exists).

**Output files** (for each prepared table, e.g. `sw`):
- `sw_clean.csv` - prepared rows without errors (rows with warnings are kept)
- `sw_failed.csv` - rows with errors, as written in the spreadsheet, with their row number
- `sw_log.xlsx` - errors, warnings and information, with the tab, row and column in the spreadsheet

A computation is left out if its software row has errors, and a datamodel if its dataset type has errors.

---

### 2. Prepare the graph for uploading to PINKKB

**Purpose:** Converts cleaned tables defining documented resources to RDF triples.
It also validates and saves the generated rdf triples serialized to turtle format.

**Usage:**
```bash
generate-graph datasettypes_clean.csv sw_clean.csv comp_clean.csv -o graph.ttl
```

**What it does:**
- Reads the clean CSV files made by `prepare-tables`
- Converts data to RDF triples using the TableDoc class from tripper
- Validates the generated RDF against SHACL shapes

**Output files:**
- `graph.ttl` - Validated RDF data in Turtle format 

**Notes:**
- Other cleaned csv's can be specified.
- The output graph filename can be changed at will.
- Requires the SSBD core ontology context (which it pulls from the web)
- If new ontology classes are used, they must be added to the context configuration
- Validates against SHACL shape definitions in the `validation/` directory

NB! This script fetches classes from the PINKKB. In order to run it you
must make a ~/.config/tripper/session.yaml file with the information
about the PINKKB.

example:
```
PINKKB:
  backend: sparqlwrapper
  base_iri: https://graphdb.pink-project.eu/repositories/pinkish
  update_iri: https://graphdb.pink-project.eu/repositories/pinkish/statements
  username: you pink kb username
  password: KEYRING
```
You can also add the password in plain text, but that is not preferred.


---

### 3. **step3_dmtable_parse.py**

**Purpose:** Parses data model definitions from CSV and converts them to RDF format, using `dlite`.

**Usage:**
```bash
python scripts/step3_dmtable_parse.py
```

**What it does:**
- Reads datamodel definitions from `datamodels.csv`
- Parses CSV using DMTable to generate data models.
- Converts datamodels to RDF triples in a triplestore
- Serializes the result to Turtle format

**Output files:**
- `datamodels.ttl` - Data models in RDF Turtle format

---

### 4. **search_pink_kb.py**

**Purpose:** Searches and queries the PINK Knowledge Base.

**Usage:**
```bash
python scripts/search_pink_kb.py
```

**What it does:**
- Loads data from multiple sources: SSBD ontology, EMMO ontology, agents, resources, and datamodels
- Provides SPARQL query capabilities over the knowledge base
- Allows searching for specific classes and their relationships
- Returns structured query results

**Notes:**
- Can be configured to connect to remote GraphDB endpoints with authentication
- Currently configured for local RDF library backend
- Includes example SPARQL queries for common searches

---

## Typical Workflow

To generate and validate all documentation:

1. **Prepare data:** Run `prepare-tables <Google spreadsheet ID>` to download, prepare and validate the tables, and correct the spreadsheet based on the logs
2. **Convert to RDF:** Run `generate-graph` on the clean tables to convert them to validated RDF triples
3. **Parse datamodels:** Run `step3_dmtable_parse.py` to convert datamodels to RDF format
4. **Query results:** Use `search_pink_kb.py` to verify and search the generated knowledge base

All steps require a valid Python environment with dependencies installed from `requirements.txt`.

## Additional helper scripts are available in the `scripts/` directory for specific tasks related to data processing and validation.
### 1. **make_drop_down_list_source.py**

**Purpose:** Generates a CSV file for drop-down lists in the annotation tool.
This is just a helper script to extract the hierarchy of assessment classes to be added to the Google Spreadsheet for annotation.

**Usage:**
```bash
python scripts/make_drop_down_list_source.py
```

**What it does:**
- Loads the SSBD core ontology
- Extracts assessment-related classes and their hierarchy (level 1, 2, and 3)
- Creates a structured CSV file with three hierarchical levels
- This CSV can be used to populate drop-down menus in annotation tools

**Output files:**
- `assessment_hierarchy.csv` - Assessment classes organized in three hierarchy levels (level1, level2, level3)




# PINK Annotation Schema (Legacy Repository)

The PINK Annotation Schema has been renamed and is now maintained as the SSBD Core Ontology.

## New Official Location

- Official documentation: https://ssbd-ontology.github.io/core/
- GitHub repository: https://github.com/ssbd-ontology/core

For ontology development, authoritative classes/properties, and ongoing updates, use the SSBD Ontology Core repository.

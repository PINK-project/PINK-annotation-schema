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
  properties, their range (the column `range`) and whether they are mandatory, recommended,
  conditional or optional. The range of a property is one or more of the following, separated by `|`
  (a value is accepted if it is one of them, e.g. `orcid | ror`):
  - predefined ranges, written in lower case:
    - `string`, `boolean`, `date`, `dateTime` (literals; cannot be combined with others)
    - `iri` (any valid IRI)
    - `url` (resolvable IRI; a URL that needs a login gives a warning)
    - `orcid` (ORCID identifier), `ror` (ROR identifier)
    - `ssbd` (a term in the SSbD Core ontology, including the terms it takes from other ontologies, e.g. `emmo:`)
    - `rights` (access right from the EU vocabulary, e.g. `rights:PUBLIC`)
    - `iana` (IANA media type, e.g. `iana:application/zip`)
  - an ontology class with a known prefix, e.g. `ssbd:Model`: the value must be that class, a subclass
    of it, or an individual of one of them. This is looked up in the SSbD Core ontology, or for
    resources documented in the same spreadsheet (e.g. a software release in `hasSoftware`) in
    their `@type` and `subClassOf`.
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

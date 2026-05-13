# PINK Annotation Schema

## Purpose of This Repository

This repository is now intended for usage of the SSBD ontology to document resources, including practical examples.
For the legacy content see below.

In order to run scripts in the current repository a working python environment is required.
Please install the python dependencies defined in `requirements.txt` with e.g.

```bash
pip install -r requirements
```

## Using the Scripts

This repository contains several scripts for generating and parsing resources documented in the 
Google Spreadsheets within the PINK project. Below is a description of each script and how to use them:

### 1. **step1_download_googledocs_resources_and_preparetables.py**

**Purpose:** Downloads and parses documentation data from Google Spreadsheets and prepares cleaned CSV files.

**Usage:**
```bash
python scripts/step1_download_googledocs_resources_and_preparetables.py
```

**What it does:**
- Downloads the data and performs data cleaning and correction
- Generates activities from the software documentation spreadsheet
- Saves cleaned data to CSV files (e.g., `sw_clean.csv`, `datasettypes_clean.csv`)
- Prepares the tables that can be directly parsed by `tripper` and `dlite`.

**Output files:**
- `sw_clean.csv` - Cleaned software documentation
- `datasettypes_clean.csv` - Cleaned dataset type documentation
- `comp_clean.csv` - Cleaned computations documentation
- `datamodels.csv` - Cleaned datamodel definitions (prepared for DMTable parsing)

---

### 2. **step2_prepare_triples.py**

**Purpose:** Converts cleaned tables defining documented resources to RDF triples.
It also validates and saves the generated rdf triples serialized to turtle format.

**Usage:**
```bash
python scripts/step2_prepare_triples.py
```

**What it does:**
- Reads the cleaned CSV files generated in step 1
- Converts data to RDF triples using the TableDoc class from tripper
- Validates the generated RDF against SHACL shapes

**Output files:**
- `pink_googlespreadsheet_resources.ttl` - Validated RDF data in Turtle format

**Notes:**
- Requires the SSBD core ontology context (which it pulls from the web)
- If new ontology classes are used, they must be added to the context configuration
- Validates against SHACL shape definitions in the `validation/` directory

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

### 4. **parse_pink_google_docs_agents.py**

**Purpose:** Parses and documents PINK agents from Google Spreadsheets.

**Usage:**
```bash
python scripts/parse_pink_google_docs_agents.py
```

**What it does:**
- Downloads agent documentation from a shared Google Spreadsheet
- Parses and corrects the agent data
- Converts to RDF triples using the SSBD core ontology
- Validates triples against SHACL shapes
- Generates structured documentation for PINK agents

**Output files:**
- `pink-agents.ttl` - Agent documentation in Turtle format

---

### 5. **search_pink_kb.py**

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

1. **Prepare data:** Run `step1_download_googledocs_resources_and_preparetables.py` to download and clean data from Google Spreadsheets
2. **Convert to RDF:** Run `step2_prepare_triples.py` to convert CSV data to validated RDF triples
3. **Parse datamodels:** Run `step3_dmtable_parse.py` to convert datamodels to RDF format
4. **Document agents:** Run `parse_pink_google_docs_agents.py` to generate agent documentation
5. **Query results:** Use `search_pink_kb.py` to verify and search the generated knowledge base

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


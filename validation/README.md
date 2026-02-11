# PINK Annotation Schema Validation

This directory contains SHACL-based validation tools for JSON-LD data conforming to the PINK annotation schema.

## Approach

The validation system uses a **generate-and-validate** approach:

1. **Shape Generation**: Ontology files (`.ttl`) in the parent directory are parsed to automatically extract class definitions, property constraints, and inheritance hierarchies
2. **SHACL Generation**: Python scripts dynamically generate SHACL (Shapes Constraint Language) shapes from the ontology
3. **Validation**: JSON-LD data files are validated against the generated SHACL shapes using `pyshacl`

This approach ensures that validation rules stay synchronized with the ontology definitions, eliminating manual maintenance of separate constraint files.

The validation operates under the **Open World Assumption (OWA)**, meaning that unknown or additional properties not defined in the ontology are permitted and will not cause validation failures. Only explicitly defined constraints (required properties, datatypes, cardinalities) are enforced.

### What is Currently Validated

The validation system covers:

- **Class types**: Verifies that resources are instances of the correct classes (e.g., `pink:Dataset`, `pink:Software`, `dcat:DataService`)
- **Required properties**: Ensures mandatory properties are present (e.g., `dcterms:title` for datasets)
- **Property datatypes**: Validates that literal values have the correct XSD datatypes
- **Property ranges**: Checks that object properties reference the appropriate classes
- **Class inheritance**: Applies constraints from parent classes (e.g., `pink:Dataset` inherits from `dcat:Resource`)

## Files

- **`generate_shacl.py`**: Main script that loads ontology files and automatically generates SHACL shapes with full inheritance support. Discovers all classes dynamically, extracts property constraints, and outputs validation rules to `shapes.ttl`.
- **`validate.py`**: Example validation scripts that loads JSON-LD data and SHACL shapes, runs validation using `pyshacl`, and returns conformance results with detailed error reports.

- **`test.py`**: Test script that orchestrates shape generation and runs validation tests on example files. Includes both valid and invalid test cases to verify the validation system works correctly.

- **`shapes.ttl`**: Auto-generated SHACL shapes file created by `generate_shacl.py`. This file contains all validation constraints extracted from the ontology and should not be edited manually. Regenerate by running `generate_shacl.py` whenever the ontology changes.

## Usage

### Generate SHACL Shapes

```bash
cd validation
python generate_shacl.py
```

This reads all `.ttl` ontology files from the parent directory and generates `shapes.ttl`.

### Validate a JSON-LD File

```python
from validation.validate import validate_jsonld, print_validation_result

conforms, report = validate_jsonld("path/to/data.jsonld")
print_validation_result("path/to/data.jsonld", conforms, report)
```

### Run Tests

```bash
cd validation
python test.py
```

This will:
1. Generate fresh SHACL shapes from the ontology
2. Validate test cases (both valid and invalid)
3. Report results and verify expected outcomes

## Requirements

- Python 3.8+
- `rdflib`: RDF parsing and graph manipulation
- `pyshacl`: SHACL validation engine

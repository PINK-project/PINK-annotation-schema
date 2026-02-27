# PINK Annotation Schema Validation

This directory contains SHACL-based validation tools for JSON-LD data conforming to the PINK annotation schema.

## Approach

The validation operates under the **Open World Assumption (OWA)**, meaning that unknown or additional properties not defined in the ontology are permitted and will not cause validation failures. Only explicitly defined constraints (required properties, datatypes, cardinalities) are enforced.

The validation system uses a **two-tier validation approach**:

1. **Auto-generated Shapes** (`shapes.ttl`): Ontology files (`.ttl`) in the parent directory are parsed to automatically extract class definitions, property constraints (datatypes, ranges), and inheritance hierarchies. These shapes mirror the ontology structure and are regenerated whenever the ontology changes.

2. **Project-specific Constraints** (`shapes-pink.ttl`): Additional validation rules specific to the PINK project that go beyond the ontology definitions, such as cardinality requirements (e.g., mandatory properties like `dcterms:title`).

3. **Validation**: JSON-LD data files are validated against **both** shape files using `pyshacl`. The validator automatically merges both constraint sets.

This two-tier approach ensures that:
- Datatype and range constraints stay synchronized with the ontology (via auto-generation)
- Project-specific requirements can be added without modifying the ontology
- Separation of concerns between ontology structure and usage requirements

### Language-Tagged Strings (rdf:langString)

In compliance with [DCAT-AP 3.0.1](https://semiceu.github.io/DCAT-AP/releases/3.0.1/), certain text properties require **language tags** for international metadata interoperability:

- `dcterms:title`
- `dcterms:description`
- `dcterms:abstract`
- `dcat:keyword`
- `skos:definition`

**Correct usage** (with language tag):
```json
"dcterms:title": {
  "@value": "Nanomaterial Toxicity Study 2025",
  "@language": "en"
}
```

**Incorrect usage** (plain string):
```json
"dcterms:title": "Nanomaterial Toxicity Study 2025"
```

If you provide a plain string without `@language`, validation will report a **datatype error** indicating that `rdf:langString` is required. This ensures metadata can support multiple languages (e.g., parallel English, German, French versions).

## Files

### Python Scripts

- **`generate_shacl.py`**: Automatically generates SHACL shapes from ontology files. Discovers all classes dynamically, extracts property constraints (datatypes, ranges, OWL restrictions), and outputs validation rules to `shapes.ttl`.

- **`validate.py`**: Validation script that loads JSON-LD data and validates it against both `shapes.ttl` and `shapes-pink.ttl`. Automatically merges both constraint sets and runs validation using `pyshacl`, returning conformance results with detailed error reports.

- **`test.py`**: Test script that orchestrates shape generation and runs validation tests on example files. Includes both valid and invalid test cases to verify the validation system works correctly.

### SHACL Shape Files

- **`shapes.ttl`**: **Auto-generated** SHACL shapes created by `generate_shacl.py`. Contains datatype and range constraints extracted directly from the ontology (e.g., `dcterms:title` must be `rdf:langString`). **Do not edit manually** - regenerate by running `generate_shacl.py` whenever the ontology changes.

- **`shapes-pink.ttl`**: **Manually maintained** project-specific SHACL constraints that extend the auto-generated shapes. Defines PINK-specific requirements such as:
  - Mandatory properties (e.g., `pink:Dataset` must have `dcterms:title` and `dcterms:description`)
  - Cardinality constraints (`sh:minCount`, `sh:maxCount`)
  - Custom validation messages

  **Important**: This file should only contain cardinality and other project-specific constraints, **not** datatype constraints (which are handled by `shapes.ttl`). Keeping datatype constraints separate ensures clearer error messages.

## Usage

### Generate SHACL Shapes

```bash
cd validation
python generate_shacl.py
```

This reads all `.ttl` ontology files from the parent directory and generates `shapes.ttl`. The project-specific constraints in `shapes-pink.ttl` are maintained separately and do not need regeneration.

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
1. Generate fresh SHACL shapes from the ontology (`shapes.ttl`)
2. Validate test cases against both `shapes.ttl` and `shapes-pink.ttl`
3. Report results and verify expected outcomes

Test cases cover various scenarios including missing properties, wrong datatypes, and plain strings instead of language-tagged strings.

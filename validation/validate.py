"""
Validate JSON-LD data against SHACL shapes.

Provides functions to validate JSON-LD files representing PINK resources
(Dataset, Software, etc.) against generated SHACL shapes.
"""
from pathlib import Path
from typing import Optional, Tuple

from pyshacl import validate as shacl_validate
from rdflib import Graph


def load_shapes(shapes_path: Path) -> Graph:
    """
    Load SHACL shapes graph from file.

    Parameters:
        shapes_path: Path to shapes.ttl file.

    Returns:
        RDF graph containing SHACL shapes.
    """
    shapes = Graph()
    shapes.parse(shapes_path, format="turtle")
    return shapes


def load_jsonld(jsonld_path: Path) -> Graph:
    """
    Parse JSON-LD file into RDF graph.

    Parameters:
        jsonld_path: Path to JSON-LD file.

    Returns:
        RDF graph containing parsed data.
    """
    data = Graph()
    data.parse(jsonld_path, format="json-ld")
    return data


def validate_jsonld(jsonld_path: str, shapes_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate JSON-LD file against SHACL shapes.

    Parameters:
        jsonld_path: Path to JSON-LD file to validate.
        shapes_path: Path to SHACL shapes file. Defaults to shapes.ttl
                     in the same directory as this script.

    Returns:
        Tuple of (conforms: bool, report: str) where conforms indicates
        if validation passed and report contains human-readable details.
    """
    jsonld_file = Path(jsonld_path)
    if not jsonld_file.exists():
        return False, f"File not found: {jsonld_path}"

    # Default shapes path
    if shapes_path is None:
        shapes_file = Path(__file__).parent / "shapes.ttl"
    else:
        shapes_file = Path(shapes_path)

    if not shapes_file.exists():
        return False, f"Shapes file not found: {shapes_file}. Run generate_shacl.py first."

    # Load data and shapes
    try:
        data_graph = load_jsonld(jsonld_file)
    except Exception as e:
        return False, f"Failed to parse JSON-LD: {e}"

    shapes_graph = load_shapes(shapes_file)

    # Run SHACL validation
    conforms, results_graph, results_text = shacl_validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",
        abort_on_first=False,
    )

    return conforms, results_text


def print_validation_result(jsonld_path: str, conforms: bool, report: str) -> None:
    """
    Print validation result in human-readable format.

    Parameters:
        jsonld_path: Path to validated file.
        conforms: Whether validation passed.
        report: Validation report text.
    """
    status = "✓ VALID" if conforms else "✗ INVALID"
    print(f"\n{status}: {jsonld_path}")
    print("-" * 60)

    if conforms:
        print("All constraints satisfied.")
    else:
        print(report)


def main() -> None:
    """Validate example files from command line."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python validate.py <jsonld_file> [shapes_file]")
        sys.exit(1)

    jsonld_path = sys.argv[1]
    shapes_path = sys.argv[2] if len(sys.argv) > 2 else None

    conforms, report = validate_jsonld(jsonld_path, shapes_path)
    print_validation_result(jsonld_path, conforms, report)

    sys.exit(0 if conforms else 1)


if __name__ == "__main__":
    main()

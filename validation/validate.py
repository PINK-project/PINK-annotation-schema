"""
Validate JSON-LD data against SHACL shapes.

Provides functions to validate JSON-LD data representing SSbD resources
(Dataset, Software, etc.) against generated SHACL shapes.
"""
import json
from pathlib import Path
from typing import Optional, Tuple, Union, cast

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


def load_graph(source: Union[str, Path, dict]) -> Graph:
    """Parse a JSON-LD file path or dict into an RDF graph."""
    graph = Graph()
    if isinstance(source, dict):
        graph.parse(data=json.dumps(source), format="json-ld")
    else:
        graph.parse(source, format="json-ld")
    return graph


def validate(
    source: Union[str, Path, dict],
    shapes_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validate JSON-LD data against SHACL shapes.

    Loads both auto-generated shapes (shapes.ttl) and project-specific
    constraints (shapes-ssbd.ttl) for validation.

    Parameters:
        source: JSON-LD source — a file path (str or Path) or a Python dict.
        shapes_path: Path to SHACL shapes file. Defaults to shapes.ttl
                     in the same directory as this script.

    Returns:
        Tuple of (conforms: bool, report: str) where conforms indicates
        if validation passed and report contains human-readable details.
    """
    if isinstance(source, (str, Path)):
        source = Path(source)
        if not source.exists():
            return False, f"File not found: {source}"

    try:
        data_graph = load_graph(source)
    except Exception as e:
        return False, f"Failed to parse JSON-LD: {e}"

    if shapes_path is None:
        shapes_file = Path(__file__).parent / "shapes.ttl"
    else:
        shapes_file = Path(shapes_path)

    if not shapes_file.exists():
        return False, f"Shapes file not found: {shapes_file}. Run generate_shacl.py first."

    shapes_graph = load_shapes(shapes_file)

    # Merge project-specific shapes if available
    ssbd_shapes_file = Path(__file__).parent / "shapes-ssbd.ttl"
    if ssbd_shapes_file.exists():
        shapes_graph.parse(ssbd_shapes_file, format="turtle")

    conforms, _results_graph, results_text = cast(
        Tuple[bool, object, str],
        shacl_validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="rdfs",
            abort_on_first=False,
        ),
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

    conforms, report = validate(jsonld_path, shapes_path)
    print_validation_result(jsonld_path, conforms, report)

    sys.exit(0 if conforms else 1)


if __name__ == "__main__":
    main()

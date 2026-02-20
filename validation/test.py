"""
Test script for SHACL validation of Dataset JSON-LD.

Generates shapes from ontology and validates example files.
"""
from pathlib import Path

from generate_shacl import generate_shapes
from validate import validate_jsonld, print_validation_result


# Define test cases declaratively
TEST_CASES = [
    {
        "filename": "tests/dataset.jsonld",
        "description": "Valid Dataset",
        "should_conform": True,
    },
    {
        "filename": "tests/dataset-invalid.jsonld",
        "description": "Invalid Dataset (wrong type for hasDatum)",
        "should_conform": False,
    },
    {
        "filename": "tests/dataset-no-title.jsonld",
        "description": "Invalid Dataset (missing required title)",
        "should_conform": False,
    },
    {
        "filename": "tests/dataset-plain-string-title.jsonld",
        "description": "Invalid Dataset (plain string instead of langString for title)",
        "should_conform": False,
    },
]


def print_header(title: str, newline_before: bool = False) -> None:
    """Print a formatted section header."""
    if newline_before:
        print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def run_tests() -> bool:
    """
    Run validation tests on example files.

    Returns:
        True if all tests pass (valid passes, invalid fails).
    """
    script_dir = Path(__file__).parent
    onto_dir = script_dir.parent
    shapes_path = script_dir / "shapes.ttl"

    # Step 1: Generate shapes
    print_header("STEP 1: Generating SHACL shapes from ontology")
    generate_shapes(onto_dir, shapes_path)

    # Step 2: Run all validation tests
    test_results = []
    for i, test_case in enumerate(TEST_CASES, start=1):
        print_header(f"STEP {i + 1}: Validating {test_case['description']}", newline_before=True)

        test_path = script_dir / test_case["filename"]
        conforms, report = validate_jsonld(str(test_path))
        print_validation_result(str(test_path), conforms, report)

        # Check if result matches expectation
        test_passed = conforms == test_case["should_conform"]
        test_results.append((test_case, conforms, test_passed))

    # Step N: Summary
    print_header("TEST SUMMARY", newline_before=True)

    for test_case, conforms, passed in test_results:
        if passed:
            status = "✓"
            outcome = "passed" if conforms else "failed"
            print(f"{status} {test_case['description']} {outcome} validation (expected)")
        else:
            status = "✗"
            outcome = "passed" if conforms else "failed"
            print(f"{status} {test_case['description']} {outcome} validation (unexpected!)")

    all_passed = all(passed for _, _, passed in test_results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))

    return all_passed


def main() -> None:
    """Run tests and exit with appropriate code."""
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

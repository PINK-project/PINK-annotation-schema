"""Command line tool: combine CSV tables into one validated Turtle graph.

Usage: generate-graph a.csv b.csv -o graph.ttl
"""

import argparse
import sys

from tripper import Triplestore
from tripper.datadoc import get_context, store
from tripper.datadoc.tabledoc import TableDoc

from pink.parseutils import PREFIXES as prefixes
from pink.pinkkb import pinkkb_classes

from validation.validate import load_shapes, shacl_validate

SHAPES = (
    "https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/"
    "gh-pages/shacl/shapes.ttl",
    "https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/"
    "gh-pages/shacl/shapes-ssbd.ttl",
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="generate graph",
        description="Combine CSV tables into one validated Turtle graph.",
    )
    parser.add_argument("csv_files", nargs="+", help="Input CSV files.")
    parser.add_argument(
        "-o", "--output", default="graph.ttl", help="Output .ttl file."
    )
    parser.add_argument(
        "--no-pinkkb",
        action="store_true",
        help="Do not look up existing classes in the PINKKB.",
    )
    args = parser.parse_args(argv)

    context = get_context("https://w3id.org/ssbd/context/", theme=None)
    if not args.no_pinkkb:
        context.add_context(pinkkb_classes())

    resources = []
    for csv_file in args.csv_files:
        doc = TableDoc.parse_csv(csv_file, context=context, prefixes=prefixes)
        resources += doc.asdicts()

    ts = Triplestore("rdflib")
    store(ts, resources, context=context, prefixes=prefixes)

    shacl_graph = load_shapes(SHAPES[0])
    shacl_graph.parse(SHAPES[1], format="turtle")

    conforms, _, report = shacl_validate(
        data_graph=ts.backend.graph,
        shacl_graph=shacl_graph,
        inference="rdfs",
        abort_on_first=False,
    )
    if not conforms:
        print("Validation failed.")
        print(report)
        return 1

    ts.serialize(args.output, format="turtle")
    print(f"Validation passed. Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

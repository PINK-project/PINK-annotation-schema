"""Command line tool: combine CSV tables into one validated Turtle graph.

Usage: generate-graph a.csv b.csv -o graph.ttl

Tables with datum columns (datumName, datumType, ...), such as datamodels_clean.csv
made by prepare-tables, are read as datamodels with dlite. Other tables are read with tripper.
"""

import argparse
import csv
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


def is_datamodel_table(csv_file):
    """Whether `csv_file` is a table of datamodels (it has datum columns)."""
    with open(csv_file, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    return any(h.strip().startswith("datumName") for h in header)


def add_datamodels(ts, csv_file):
    """Add the datamodels in `csv_file` to the triplestore `ts`, using dlite."""
    from dlite.table import DMTable

    with open(csv_file, newline="", encoding="utf-8") as f:
        table = list(csv.reader(f))
    # Units that are not in EMMO are left out (prepare-tables warns about them)
    DMTable(table, unit_handling="ignore").to_triplestore(ts)


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

    datamodel_files = [f for f in args.csv_files if is_datamodel_table(f)]
    resources = []
    for csv_file in args.csv_files:
        if csv_file not in datamodel_files:
            doc = TableDoc.parse_csv(csv_file, context=context, prefixes=prefixes)
            resources += doc.asdicts()

    ts = Triplestore("rdflib")
    store(ts, resources, context=context, prefixes=prefixes)
    for csv_file in datamodel_files:
        add_datamodels(ts, csv_file)

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

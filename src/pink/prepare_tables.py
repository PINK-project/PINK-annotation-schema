"""Command line tool: prepare and validate documentation tables for generate-graph.

Usage:
    prepare-tables SOURCE [--type TYPE] [--sheet NAME] [-o FOLDER]

SOURCE is the ID of a Google spreadsheet, an Excel file or a CSV file.

In a Google spreadsheet or Excel file, the tabs are recognised by their name:
    Software...    -> software     (sw_clean.csv and comp_clean.csv)
    Computation... -> computation  (computations_clean.csv)
    Dataset Type   -> datasettype  (datasettypes_clean.csv and datamodels.csv)
    Dataset        -> dataset      (datasets_clean.csv)
All recognised tabs are prepared, or only the one given with --type.
Another tab can be used with --sheet, and a CSV file has no tabs.
In these cases the type is given with --type, or asked for.

Each prepared table is validated against its profile in profiles/.
Rows with errors are left out of <name>_clean.csv and written to <name>_failed.csv,
and all messages are written to <name>_log.xlsx, with the tab, row and column
in the spreadsheet.
"""

import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd
import requests

TYPES = ("software", "computation", "datasettype", "dataset")

GOOGLE_XLSX = "https://docs.google.com/spreadsheets/d/{}/export?format=xlsx"


def tab_type(name):
    """Return the type of table in a tab with this name, or None."""
    name = name.strip().lower()
    if name.startswith("software"):
        return "software"
    if name.startswith("computation"):
        return "computation"
    if name == "dataset type":
        return "datasettype"
    if name == "dataset":
        return "dataset"
    return None


def date_as_shown(value, number_format):
    """Return a date cell as the text shown in the spreadsheet,
    e.g. 'January 2015' for the format 'mmmm yyyy'."""
    fmt = re.sub(r'\[[^\]]*\]|["\\]', "", number_format.split(";")[0]).lower()
    tokens = re.findall(r"y+|m+|d+|h+|s+|.", fmt)
    parts = [t[0] for t in tokens if t[0] in "ymdhs"]
    text = []
    for i, t in enumerate(tokens):
        n = len(t)
        if t[0] == "m":  # month, or minutes when next to hours or seconds
            k = sum(1 for x in tokens[:i] if x[0] in "ymdhs")
            minute = n <= 2 and ((k > 0 and parts[k - 1] == "h") or (k + 1 < len(parts) and parts[k + 1] == "s"))
            if minute:
                text.append(f"{value.minute:0{n}d}")
            else:
                text.append({1: str(value.month), 2: f"{value.month:02d}", 3: value.strftime("%b")}.get(n, value.strftime("%B")))
        elif t[0] == "y":
            text.append(value.strftime("%Y") if n > 2 else value.strftime("%y"))
        elif t[0] == "d":
            text.append({1: str(value.day), 2: f"{value.day:02d}", 3: value.strftime("%a")}.get(n, value.strftime("%A")))
        elif t[0] == "h":
            text.append(f"{value.hour:0{min(n, 2)}d}")
        elif t[0] == "s":
            text.append(f"{value.second:0{min(n, 2)}d}")
        else:
            text.append(t)
    return "".join(text)


def read_excel(file):
    """Return a dict mapping tab name to table, with all cells as text.
    Date cells get the text shown in the spreadsheet (as in the CSV export
    of a Google spreadsheet), so that e.g. a version is not turned into a date."""
    workbook = openpyxl.load_workbook(file, data_only=True)
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if getattr(cell, "is_date", False) and isinstance(cell.value, date):
                    cell.value = date_as_shown(cell.value, cell.number_format)
    return pd.read_excel(workbook, sheet_name=None, dtype=str, engine="openpyxl")


def read_source(source):
    """Return a dict mapping tab name to table (None as name for a CSV file).
    All cells are read as text."""
    path = Path(source)
    if path.suffix.lower() == ".csv":
        return {None: pd.read_csv(path, dtype=str)}
    if path.suffix.lower() == ".xlsx":
        return read_excel(path)
    # Otherwise the ID of a Google spreadsheet: download it as Excel
    response = requests.get(GOOGLE_XLSX.format(source), timeout=60)
    response.raise_for_status()
    return read_excel(io.BytesIO(response.content))


def ask(question, choices):
    """Ask the user to choose one of `choices`."""
    if not sys.stdin.isatty():
        sys.exit(f"{question} Please choose one of: {', '.join(choices)}")
    while True:
        answer = input(f"{question} [{'/'.join(choices)}]: ").strip()
        if answer in choices:
            return answer


def select_tables(sheets, table_type=None, sheet=None):
    """Return a dict mapping type to (tab name, table)."""
    if sheet is not None:
        if sheet not in sheets:
            sys.exit(f"No tab '{sheet}'. The tabs are: {', '.join(sheets)}")
        table_type = table_type or ask(f"Which type of table is tab '{sheet}'?", TYPES)
        return {table_type: (sheet, sheets[sheet])}

    if None in sheets:  # CSV file
        table_type = table_type or ask("Which type of table is the CSV file?", TYPES)
        return {table_type: (None, sheets[None])}

    found = {tab_type(name): name for name in sheets if tab_type(name)}
    if table_type:
        found = {t: name for t, name in found.items() if t == table_type}
    if not found:
        sheet = ask("No known tab found. Which tab should be used?", list(sheets))
        return select_tables(sheets, table_type, sheet)
    return {t: (name, sheets[name]) for t, name in found.items()}


def source_columns(name, raw):
    """Return a dict mapping each property in prepared table `name`
    to the spreadsheet column(s) it comes from."""
    from pink.parseutils import property_iri_dict

    columns = {property_iri_dict.get(col, col): col for col in raw.columns}
    columns["@type"] = "(added by the tool)"
    ssbd_cols = [col for col in raw.columns if col.startswith("SSbD Assessment")]
    if name == "sw":
        columns["chemicalClass"] = ", ".join(col for col in raw.columns if col.startswith("chemicalClass[by"))
    if name == "comp":  # made from the software tab
        columns["@id"] = "identifier (generated from)"
        columns["hasSoftware"] = "identifier"
        columns["label"] = "title (generated from)"
        columns["description"] = "title (generated from)"
    if name in ("comp", "computations"):
        columns["subClassOf"] = ", ".join(ssbd_cols)
    return columns


def report(errors, tab, raw, prepared, columns):
    """Return the error table in terms of the spreadsheet: tab, row and column."""
    rows = errors["row"]
    return pd.DataFrame({
        "tab": tab if tab is not None else "(CSV file)",
        "row": pd.array([int(r) + 2 if pd.notna(r) else None for r in rows], dtype="Int64"),  # row 1 is the header
        "identifier": [prepared["@id"].get(int(r)) if pd.notna(r) else None for r in rows],
        "column": [columns.get(c, c) for c in errors["column"]],
        "property": errors["column"],
        "type": errors["type"],
        "message": errors["message"],
    })


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="prepare-tables",
        description="Prepare and validate documentation tables for generate-graph.",
    )
    parser.add_argument("source", help="Google spreadsheet ID, Excel file or CSV file.")
    parser.add_argument("--type", choices=TYPES, help="Type of table.")
    parser.add_argument("--sheet", help="Name of the tab to use.")
    parser.add_argument("-o", "--output", default=".", help="Output folder (default: current folder).")
    parser.add_argument("-c", "--credentials", default="credentials.json",
                        help="File with web service credentials (optional, without it ORCIDs are looked up anonymously).")
    parser.add_argument("--profiles", default=str(Path(__file__).resolve().parents[2] / "profiles"),
                        help="Folder with the validation profiles.")
    args = parser.parse_args(argv)

    sheets = read_source(args.source)
    tables = select_tables(sheets, args.type, args.sheet)
    for table_type, (name, _) in tables.items():
        print(f"{table_type}: {'CSV file' if name is None else 'tab ' + repr(name)}")

    # Imported here, since they are slow to load
    from types import SimpleNamespace

    from ontopy import get_ontology
    from tripper.datadoc import get_context, get_keywords
    from tripper.datadoc.errors import InvalidKeywordError
    from tripper.datadoc.tabledoc import Column

    import pink.validateutils
    from pink.parseutils import PREFIXES
    from pink.prepare import (
        prepare_computations,
        prepare_datamodels,
        prepare_datasets,
        prepare_datasettypes,
        prepare_software,
    )

    onto = get_ontology("https://ssbd-ontology.github.io/core/core-inferred.ttl").load()
    kw = get_keywords(theme=None)
    kw.load_yaml(
        "https://raw.githubusercontent.com/ssbd-ontology/core/refs/"
        "heads/gh-pages/context/keywords.yaml",
        redefine="allow",
    )
    context = get_context("https://w3id.org/ssbd/context/", theme=None)
    credentials = pink.validateutils.read_credentials(SimpleNamespace(credentials_file=args.credentials))
    # Prefixes known in validation: those of the SSbD context and the PINK prefixes
    prefixes = {k: v for k, v in context.get_prefixes().items() if k} | PREFIXES

    # Prepare: (name of the output, profile, tab, rows of the tab, prepared table)
    prepared = []
    datamodels = None
    for table_type, (tab, raw) in tables.items():
        raw = raw.loc[:, ~raw.columns.astype(str).str.startswith("Unnamed:")]
        if table_type == "software":
            expanded_sw, expanded_comp = prepare_software(raw, onto, context)
            prepared.append(("sw", "software", tab, raw, expanded_sw))
            prepared.append(("comp", "computation", tab, raw, expanded_comp))
        elif table_type == "computation":
            prepared.append(("computations", "computation", tab, raw, prepare_computations(raw, onto, context)))
        elif table_type == "datasettype":
            datamodels = prepare_datamodels(raw)
            prepared.append(("datasettypes", "datasettype", tab, raw, prepare_datasettypes(raw, onto, context)))
        elif table_type == "dataset":
            prepared.append(("datasets", "dataset", tab, raw, prepare_datasets(raw, onto, context)))

    # Validate each prepared table against its profile, and leave out the rows with errors
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    failed = {}
    for name, profile, tab, raw, table in prepared:
        print(f"\nVALIDATING {name} against profile {profile}")
        profile_table = pink.validateutils.read_profile_table(
            SimpleNamespace(profile_file=str(Path(args.profiles) / f"{profile}.csv")))
        errors = pink.validateutils.validate_table(table, profile_table, onto, credentials, prefixes)

        # Columns that tripper does not know make generate-graph fail for the whole table
        for header in table.columns:
            try:
                Column(header, context=context)
            except InvalidKeywordError:
                errors = pink.validateutils.add_error(
                    errors, None, header.removesuffix("[?sep=;]"), "Error",
                    "Unknown column: not a keyword of the SSbD context. "
                    "If it is a comment for the curators, add (comment) to the column name.")

        # Rows that were dropped in the preparation, because they have no identifier
        for row in raw.index.difference(table.index):
            if raw.loc[row].notna().any():
                errors = pink.validateutils.add_error(errors, row, "@id", "Error", "No identifier: the row is left out.")
        # A computation made from the software tab is left out if its software is
        if name == "comp":
            for row in table.index.intersection(failed.get("sw", [])):
                errors = pink.validateutils.add_error(errors, row, "hasSoftware", "Error", "The software in this row has errors: the computation is left out.")

        log = report(errors, tab, raw, table, source_columns(name, raw))
        pink.validateutils.write_error_table(out / f"{name}_log.xlsx", log)

        failed_rows = errors.loc[errors["type"] == "Error", "row"]
        if failed_rows.isna().any():  # a missing mandatory column (no row number): every row fails
            failed[name] = raw.index
        else:
            failed[name] = raw.index.intersection(failed_rows.astype(int).unique())
        failed_table = raw.loc[failed[name]]
        failed_table.insert(0, "row", failed_table.index + 2)
        failed_table.to_csv(out / f"{name}_failed.csv", index=False)
        table.drop(index=table.index.intersection(failed[name])).to_csv(out / f"{name}_clean.csv", index=False)
        print(f"{name}: {len(table.index.difference(failed[name]))} rows in {name}_clean.csv, "
              f"{len(failed[name])} rows with errors in {name}_failed.csv, messages in {name}_log.xlsx")

    if datamodels is not None:  # leave out the datamodels of dataset types with errors
        datamodels.drop(index=datamodels.index.intersection(failed["datasettypes"])).to_csv(out / "datamodels.csv", index=False)
    print(f"Prepared tables written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

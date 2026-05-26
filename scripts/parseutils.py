"""
Utility functions for parsing and correcting the dataframes from the spreadsheet.
"""

import re
import sys
from pathlib import Path

import dateutil
import pandas as pd
from ontopy.exceptions import NoSuchLabelError

sys.path.append(str(Path(__file__).resolve().parents[1]))


TERMDEF_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&"
    "gid=896757873"
)

PREFIXES: dict[str, str] = {
    "mw": "https://modelwave.it/",
    "rights": "http://publications.europa.eu/resource/authority/access-right/",
    "datasettype": "https://pink-project.eu/datasettype/",
    "qsar": "https://pink-project.eu/qsar/",
    "pink": "https://pink-project.eu/",
    "empa": "https://empa.ch/",
    "empadm": "https://empa.ch/datamodel/",
    "oboowl": "http://www.geneontology.org/formats/oboInOwl#",
    "obo": "http://purl.obolibrary.org/obo/",
    "chemowl": "http://www.semanticweb.org/ontologies/cheminf.owl#",
    "cheminf": "http://semanticscience.org/resource/",
    "omics": "http://pink-project.eu/omics/",
}


def _load_termdefs() -> pd.DataFrame:
    """Read the fixed term definitions spreadsheet."""
    return pd.read_csv(TERMDEF_URL, skiprows=2)


_TERMDEFS = _load_termdefs()

list_columns: list[str] = [
    *_TERMDEFS.loc[
        _TERMDEFS["SingleValue"] == False, "Tripper_keyword"
    ].tolist(),
    "@id",
    "@type",
]

property_iri_dict: dict[str, str] = {
    prop: iri
    for prop, iri in zip(_TERMDEFS["Property"], _TERMDEFS["Tripper_keyword"])
}


def convert_to_iri(value, prefixes=PREFIXES):
    """
    Convert a value to an IRI if it starts with a known prefix.
    If the value is empty or NaN, return it as is."""
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    value = str(value).strip()
    for prefix, iri in prefixes.items():
        if value.startswith(prefix + ":"):
            return value.replace(prefix + ":", iri)
    return value


def add_prefix(value, prefix="pink"):
    """Add prefix to value if it does not already have one and is not empty.
    If the value is a list, apply the function to each element in the list and return a new list.
    """
    if isinstance(value, list):
        return [add_prefix(v, prefix) for v in value]
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    value = str(value).strip()
    if (
        not value.startswith("http://")
        and not value.startswith("https://")
        and ":" not in value
    ):
        return ":".join([prefix, value])
    return value


def remove_extra_text(value):
    """Correct the value by removing everything after
    the first space.

    For pink, this is done specifically in the tierLevel column,
    as some curators desired explanations on the tier level,
    which should be removed.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    return value.strip().split(" ")[0]


def merge_columns(row, class_cols, prefix=None):
    """
    Merge values from multiple columns into a single list.

    If `prefix` is given (e.g. ``"ssbd"``), it is prepended to each value
    that does not already contain a colon (i.e. is not already a prefixed
    name or IRI).
    """
    values = []

    for col in class_cols:
        cell = row[col]

        if isinstance(cell, list):
            parts = cell

        elif pd.isna(cell):
            continue
        else:
            parts = str(cell).split(",")

        # Clean whitespace and optionally add prefix
        cleaned = [p.strip() for p in parts if p.strip()]
        if prefix:
            cleaned = add_prefix(cleaned, prefix)
        values.extend(cleaned)

    return values


def split_to_list(value):
    """
    Split value to a list on comma, semicolon, pipe, or space,
    and clean whitespace.
    Return None if empty or NaN.
    Return value as is if it is not a string (e.g. already a list).
    """
    if not isinstance(value, str):
        return value  # Return as is if not a string
    if pd.isna(value) or str(value).strip() == "":
        return None  # Return None if empty or NaN
    # Split on comma, semicolon, pipe, or space
    parts = re.split(r"[,\s;|]+", value)
    # Clean whitespace and remove empty strings
    cleaned = [p.strip() for p in parts if p.strip() != ""]
    return cleaned


def expand_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand the dataframe: Any column whose values are lists
    will be expanded into multiple columns (all using the same header),
    with blanks where the lists were shorter.
    """
    # reindex
    df = df.reset_index(drop=True)

    parts = []
    for col in df.columns:
        is_list_col = df[col].apply(lambda v: isinstance(v, list)).any()
        if is_list_col:
            print("column", col, "is a list column")
            sub = pd.DataFrame(
                df[col]
                .apply(lambda v: v if isinstance(v, list) and v else [None])
                .tolist()
            )
            sub.columns = [col] * sub.shape[1]
            parts.append(sub)
        else:
            parts.append(df[[col]])

    out = pd.concat(parts, axis=1)
    # clean the output (not the original df)
    out = out.map(lambda x: x.strip() if isinstance(x, str) else x)
    out = out.replace(r"^\s*$", "", regex=True).fillna("")

    return out


def check_for_uris(df: pd.DataFrame, ontology) -> pd.DataFrame:
    """
    Check all values in the dataframe.
    If they are a URI (starting with http://, https://, or prefix:),
    check that they exist in the ontology. If so, replace with the IRI.
    """

    def case_variations(text: str) -> list[str]:
        """Return unique case variants for ontology lookup.
        This is a bit risky since there is not reason this will work.
        In particular acronyms will not work."""
        candidates = [
            text,
            text.lower(),
            text.upper(),
            text.title(),
            text.capitalize(),
        ]
        # Preserve order while removing duplicates.
        return list(dict.fromkeys(candidates))

    def process_value(val):
        """
        Do the analysis of the value to find if it corresponds to an IRI
        in the ontology.
        This is done only because people do not want to use the
        IRIs directly but prefer to use rdfs:label
        """
        if not isinstance(val, str):
            return val

        val = val.strip()
        if not val:
            return val

        # Detect URI-like values
        if (
            val.startswith("http://")
            or val.startswith("https://")
            or ":" in val
        ):
            lookup_val = val

            # Remove prefix if not full URI
            # Careful! We here remove the prefix and therefore risk
            # using the wrong terms in the lookup
            # OK, here as long as we only use one ontology
            # Also: the ontology lookup will not always work
            # since we are now using labels that don't exist as
            # eny kind of labels in the ontology. rdfs:labels are
            # preferably in lower case
            if not (val.startswith("http://") or val.startswith("https://")):
                lookup_val = val.split(":", 1)[1]

            for candidate in case_variations(lookup_val.strip()):
                try:
                    term = ontology.get_by_label(candidate)
                    print(f"Replacing {val} with IRI: {term.iri}")
                    return term.iri
                except (NoSuchLabelError, AttributeError):
                    pass

            # If there is a space in the value return unchanged,
            # as a real URI cannot have spaces.
            if " " in val:
                print(
                    f"Value '{val}' looks like a URI but contains spaces. Smart to check this."
                )
            return val
        return val

    df = df.map(process_value)
    return df


def correct_pink_dataframes(df, ontology):
    """
    Correct the pink dataframes by:
    - Adding prefixes to values in certain columns
    - Merging class columns into a single column
    - Splitting columns with multiple values into lists
    - Checking for URIs and replacing with IRIs from the ontology
    """
    # Remove columns that have nan as header (these are from empty columns in the spreadsheet)
    df = df.loc[:, ~df.columns.isna()]
    # Remove all columns starting with 'Datum' (these go into the datamodel)
    df = df.drop(
        columns=[col for col in df.columns if col.startswith("datum")]
    )
    # Remove Unamed columns
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    # Remove the all columns that have '(comment)' in their name
    # These are for the curators filling out the spreadsheet and should
    # be looked at with them.
    df = df.drop(columns=[col for col in df.columns if "(comment)" in col])
    df.rename(columns=property_iri_dict, inplace=True)
    #  remove rows with empty @id
    df.dropna(subset=["@id"], inplace=True)
    # Convert releaseDate to ISO format (YYYY-MM-DD)
    if "releaseDate" in df.columns:
        df["releaseDate"] = df["releaseDate"].apply(
            lambda x: (
                dateutil.parser.parse(x).isoformat() if pd.notna(x) else None
            )
        )

    # correct tier level
    if "tierLevel" in df.columns:
        df["tierLevel"] = df["tierLevel"].apply(remove_extra_text)

    # Add prefixes to values
    if "accessRights" in df.columns:
        df["accessRights"] = df["accessRights"].apply(
            add_prefix, prefix="rights"
        )

    for col in ["tierLevel", "@id"]:
        if col in df.columns:
            df[col] = df[col].apply(add_prefix, prefix="pink")

    # Change possible lists to lists
    for col in set(list_columns).intersection(df.columns):
        print(col)
        df[col] = df[col].apply(split_to_list)
    expanded_df = expand_df(df)
    expanded_df = check_for_uris(expanded_df, ontology)

    return expanded_df

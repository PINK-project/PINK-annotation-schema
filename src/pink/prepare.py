"""
Preparation of the tables in the PINK documentation spreadsheet.

- The software tab gives a software table and a computation (activity) table.
- A computation tab gives a computation table.
- The dataset type tab gives a dataset type table and a datamodel table.
- The dataset tab gives a dataset table.

The prepared tables can be parsed directly by tripper (see generate-graph).
Their index is the row in the input tab (0 is the first row below the header),
so that feedback can be given on the original spreadsheet.
"""

import pandas as pd

from pink.parseutils import PREFIXES as prefixes
from pink.parseutils import (
    correct_pink_dataframes,
    merge_columns,
    property_iri_dict,
)


def prepare_software(sw, onto, context):
    """Return the prepared software table and computation table
    made from the software tab."""
    sw = sw.copy()
    # Create the computatations documentation dataframe,
    # and copy/move relevant columns from the software documentation dataframe.
    ssbd_cols = [col for col in sw.columns if col.startswith("SSbD Assessment")]

    activity_columns = [
        "inputDatasetType",
        "outputDatasetType",
        "outputsIndicator",
    ] + ssbd_cols

    comp = sw[activity_columns + ["title", "curator"]]
    sw = sw.drop(columns=activity_columns)

    # Generate label and description of the computation from the software title.
    # The curator is the same as for the software (copied above).
    software_title = comp["title"].apply(lambda t: " ".join(t.split()) if isinstance(t, str) else t)
    # tripper uses class labels as JSON-LD terms, which must not contain ":"
    comp["label"] = "Computation with " + software_title.str.replace(":", "")
    comp["description"] = "Computation performed with the software " + software_title + "."

    # Correct software documentation dataframe
    print("PREPARING SW DOCUMENTATION")
    # Clean up the chemicalClass,
    # which is currently in three columns for easier annotation in the spreadsheet.
    chemicalclass_cols = [
        "chemicalClass[by type]",
        "chemicalClass[by size]",
        "chemicalClass[by functionality]",
    ]
    sw["chemicalClass"] = sw.apply(
        merge_columns, axis=1, class_cols=chemicalclass_cols
    )
    sw.drop(columns=chemicalclass_cols, inplace=True)

    # We have to decide how to handle Indicator, it is currently a class.
    if "indicator" in sw.columns:
        sw = sw.drop(columns=["indicator"])

    sw["@type"] = "ssbd:Software"

    expanded_sw = correct_pink_dataframes(sw, onto, context, verbose=False)

    # Make sure that the activity is related to the sofware.
    # comp and expanded_sw share the index (row in the software tab), so
    # each activity gets the software from its own row. Activities whose
    # software row was dropped get no hasSoftware and no @id, and are dropped.
    comp["hasSoftware"] = expanded_sw["@id"]

    expanded_comp = prepare_computations(comp, onto, context)
    return expanded_sw, expanded_comp


def prepare_computations(comp, onto, context):
    """Return the prepared computation table, made from a computation tab
    or from the computation columns of the software tab."""
    comp = comp.copy()
    # Correct the computations documentation dataframe
    ssbd_cols = [col for col in comp.columns if col.startswith("SSbD Assessment")]

    # Create a unique id (@id) for each activity in the comp dspreadsheet
    # Rules:  pinksw changes to pinkonto prefix
    # The name in the IRI (last values after /) is converted to activity_{name}
    # If it is not a valid iri just add activity_ in front.

    # (Only if the table has no identifier column, as when made from the software tab.)
    if "@id" not in [property_iri_dict.get(col, col) for col in comp.columns]:
        values = comp["hasSoftware"].astype(str).str.replace(
            r"^pinksw:", "pinkonto:", regex=True
        )

        comp["@id"] = values.str.replace(
            r"([^/:]+)$", r"activity_\1", regex=True
        ).where(comp["hasSoftware"].notna())

    # Add a column that defines that each activity is a prov:Activity and ssbd:Computation
    # Reasoning tells us that a ssbd:Computation is a prov:Activity, but we add both for easier
    # querying and to avoid relying on reasoning in the triplestore.
    comp["@type"] = "owl:Class"

    subclassof = ["prov:Activity", "ssbd:Computation"]
    comp["subClassOf"] = comp.apply(
        merge_columns,
        axis=1,
        class_cols=ssbd_cols,
        prefix="ssbd",
    ).apply(lambda x: list(dict.fromkeys((x or []) + subclassof)))

    comp.drop(
        columns=ssbd_cols,
        inplace=True,
    )

    return correct_pink_dataframes(comp, onto, context, verbose=False)


def prepare_datamodels(datasettypes):
    """Return the datamodel table made from the datum columns
    in the dataset type tab."""
    # Make a datamodel dataframe from the dataset documentation, by selecting the columns that start with "Datum"
    # @id will be set to the value in column "datamodel"
    datamodels = datasettypes[
        [col for col in datasettypes.columns if col.startswith("datum")]
    ]

    # Set @id to the value in column "datamodel" if it exists, otherwise to the same value as in datasettypes["identifier"]
    datamodels["@id"] = datasettypes.apply(
        lambda row: (
            row["datamodel"]
            if pd.notna(row["datamodel"]) and str(row["datamodel"]).strip() != ""
            else row["identifier"]
        ),
        axis=1,
    )

    # remove rows with empty @id
    datamodels = datamodels[
        datamodels["@id"].notna() & (datamodels["@id"].str.strip() != "")
    ]

    # convert datamodel @id to be an iri using the prefix mapping in prefixes
    # the @id is already written with a prefix, so we can just replace the prefix with the corresponding IRI
    def convert_id_to_iri(value):
        if pd.isna(value) or str(value).strip() == "":
            return value  # Return as is if empty or NaN
        value = str(value).strip()
        for prefix, iri in prefixes.items():
            if value.startswith(prefix + ":"):
                return value.replace(prefix + ":", iri)
        return value

    datamodels["@id"] = datamodels["@id"].apply(convert_id_to_iri)

    datamodels["description"] = datasettypes["identifier"].apply(
        lambda x: f"This is the datamodel for {x}"
    )

    # Are both title and description really necessary?
    datamodels["title"] = datasettypes["identifier"].apply(
        lambda x: f"{x}-datamodel"
    )

    # remove all rows that have all fields starting with "datum" empty
    datamodels = datamodels[
        ~(datamodels.filter(regex="^datum").isna().all(axis=1))
    ]
    return datamodels


def prepare_datasettypes(datasettypes, onto, context):
    """Return the prepared dataset type table made from the dataset type tab."""
    datasettypes = datasettypes.copy()
    # Datasettype
    print("PREPARING DATASETTYPE DOCUMENTATION")
    # Drop indicator
    datasettypes["@type"] = [["owl:Class"]] * len(datasettypes)

    datasettypes = datasettypes.drop(columns=["indicator"])
    expanded_datasettypes = correct_pink_dataframes(datasettypes, onto, context, verbose=False)
    return expanded_datasettypes


def prepare_datasets(datasets, onto, context):
    """Return the prepared dataset table made from the dataset tab.
    The dataset tab already uses the tripper keywords as column names."""
    print("PREPARING DATASET DOCUMENTATION")
    return correct_pink_dataframes(datasets, onto, context, verbose=False)

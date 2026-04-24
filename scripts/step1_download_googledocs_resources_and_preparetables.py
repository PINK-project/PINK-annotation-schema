"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documentation.
"""

import sys
from pathlib import Path

import pandas as pd
from ontopy import get_ontology
from tripper import Triplestore
from tripper.datadoc import (
    get_context,
    get_keywords,
)


sys.path.append(str(Path(__file__).resolve().parents[1]))


from parseutils import (
    PREFIXES as prefixes,
    convert_to_iri,
    correct_pink_dataframes,
    merge_columns,
)



# import the pink ontology for accessing labels and
# convert to IRIs (just before storing into the triplestore)
onto = get_ontology("https://ssbd-ontology.github.io/core/core-inferred.ttl").load()

# Get data from Google Sheets
# Software documentation
SW_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&"
    "gid=1707023773"
)
sw = pd.read_csv(SW_URL)

# Dataset documentation
DATASETTYPE_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&"
    "gid=1581267372"
)
datasettypes = pd.read_csv(DATASETTYPE_URL)

# Make a datamodel dataframe from the dataset documentation, by selecting the columns that start with "Datum"
# @id will be set to the value in column "datamodel"
datamodels = datasettypes[
    [col for col in datasettypes.columns if col.startswith("datum")]
]

# Set @id to the value in column "datamodel" if it exists, otherwise to the same value as in datasettypes["identifier"]
datamodels["@id"] = datasettypes.apply(
    lambda row: row["datamodel"] if pd.notna(row["datamodel"]) and str(row["datamodel"]).strip() != "" else row["identifier"],
    axis=1,
)

# convert datamodel @id to be an iri using the prefix mapping in prefixes
# the @id is already written with a prefix, so we can just replace the prefix with the corresponding IRI
def convert_to_iri(value):
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    value = str(value).strip()
    for prefix, iri in prefixes.items():
        if value.startswith(prefix + ":"):
            return value.replace(prefix + ":", iri)
    return value   
datamodels["@id"] = datamodels["@id"].apply(convert_to_iri)


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

# save a csv of the datamodel
datamodels.to_csv("datamodels.csv", index=False)


# Get pink keywords
kw = get_keywords(theme=None)
kw.load_yaml(
    "https://raw.githubusercontent.com/ssbd-ontology/core/refs/"
    "heads/gh-pages/context/keywords.yaml",
    redefine="allow",
)

context = get_context(
    "https://w3id.org/ssbd/context/", theme=None
)
# Create the computatations documentation dataframe,
# and copy/move relevant columns from the software documentation dataframe.
ssbd_cols = [col for col in sw.columns if col.startswith("SSbD Assessment")]

activity_columns = [
    "inputDatasetType",
    "outputDatasetType",
] + ssbd_cols

comp = sw[activity_columns + ["title"]]
sw = sw.drop(columns=activity_columns)

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
sw = sw.drop(columns=["indicator"])

sw["@type"] = "pink:Software"

expanded_sw = correct_pink_dataframes(sw, onto)
# A bit cumbersome to write file, I am sure there are better ways

expanded_sw.to_csv("sw_clean.csv", index=False)

# Correct the computations documentation dataframe

#print("PREPARING COMPUTATION TYPE DOCUMENTATION")
# Create a unique id (@id) for each activity in the comp dspreadsheet

comp["@id"] = comp.apply(
    lambda row: f"https://w3id.org/pink/activity/activity{row.name}", axis=1
)
# Add a column that defines that each activity is a prov:Activity and pink:Computation
# Reasoning tells us that a pink:Computation is a prov:Activity, but we add both for easier
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

expanded_comp = correct_pink_dataframes(comp, onto)
expanded_comp.to_csv("comp_clean.csv", index=False)

# Datasettype
print("PREPARING DATASETTYPE DOCUMENTATION")
# Drop indicator
datasettypes["@type"] = [["owl:Class"]] * len(datasettypes)

datasettypes = datasettypes.drop(columns=["indicator"])
expanded_datasettypes = correct_pink_dataframes(datasettypes, onto)
expanded_datasettypes.to_csv("datasettypes_clean.csv", index=False)



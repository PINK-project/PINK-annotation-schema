"""
Script used to parse the google spreadsheet used by the
model and dataset providers for documentation.
"""

import json
import re
import sys
from pathlib import Path

import dateutil
import pandas as pd
from ontopy import get_ontology
from ontopy.exceptions import NoSuchLabelError
from tripper import Triplestore
from tripper.datadoc import (
    get_context,
    get_keywords,
    told,
    search,
)

from dlite.table import DMTable

from tripper.datadoc.tabledoc import TableDoc
import keyring

sys.path.append(str(Path(__file__).resolve().parents[1]))

# pylint: disable=wrong-import-position,import-error
from validation.validate import load_shapes, shacl_validate


def add_prefix(value, prefix="pink"):
    """Add prefix to value if it does not already have one and is not empty.
    If the value is a list, apply the function to each element in the list and return a new list.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    if isinstance(value, list):
        return [add_prefix(v, prefix) for v in value]
    value = str(value).strip()
    if (
        not value.startswith("http://")
        and not value.startswith("https://")
        and ":" not in value
    ):
        return ":".join([prefix, value])
    return value


def correct_tier_level(value):
    """Correct the tierLebel to remove the
    explanatory label.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    return value.strip().split(" ")[0]


def merge_classes(row, class_cols):
    """
    Merge values from multiple class columns into a single list.
    """
    values = []

    for col in class_cols:
        cell = row[col]

        if pd.notna(cell) and str(cell).strip() != "":
            # Split on comma
            parts = str(cell).split(",")

            # Clean whitespace and add
            cleaned = [p.strip() for p in parts if p.strip() != ""]
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

    def process_value(val):
        if not isinstance(val, str):
            return val

        # Detect URI-like values
        if (
            val.startswith("http://")
            or val.startswith("https://")
            or ":" in val
        ):
            lookup_val = val

            # Remove prefix if not full URI
            # OBS! vi risikerer å bruke feil prefix.
            if not (val.startswith("http://") or val.startswith("https://")):
                lookup_val = val.split(":", 1)[1]
            try:
                term = ontology[lookup_val]
                print(f"Replacing {val} with IRI: {term.iri}")
                return term.iri
            except NoSuchLabelError:
                # If there is a space in the value return None,
                # As areal uri cannot have spaces
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
    df.rename(columns=property_to_iri, inplace=True)
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
        df["tierLevel"] = df["tierLevel"].apply(correct_tier_level)

    # Add prefixes to values
    if "accessRights" in df.columns:
        df["accessRights"] = df["accessRights"].apply(
            add_prefix, prefix="rights"
        )

    for col in ["tierLevel", "@id"]:
        if col in df.columns:
            df[col] = df[col].apply(add_prefix, prefix="pink")

    # Change possible lists to lists
    #print("columns", df.columns)
    for col in set(list_columns).intersection(df.columns):
        df[col] = df[col].apply(split_to_list)
    #print("after split_to_list", df.columns)
    expanded_df = expand_df(df)
    #print("after expand_df", expanded_df.columns)
    expanded_df = check_for_uris(expanded_df, ontology)

    return expanded_df


def merge_ssbd_assessments(row):
    """
    merge the values from the columns starting with "SSbD Assessment" into a list.
    """
    values = []
    ssbd_cols = [col for col in row.index if col.startswith("SSbD Assessment")]
    for col in ssbd_cols:
        cell = row[col]

        if pd.notna(cell) and str(cell).strip() != "":
            # Split on comma
            parts = str(cell).split(",")

            # Clean whitespace and add
            cleaned = ["ssbd:" + p.strip() for p in parts if p.strip() != ""]
            values.extend(cleaned)

    return values


# Choice of prefixes
prefixes = {
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
    "omics": "http://pink-project.eu/omics/",
}



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

# Term definitions
TERMDEF_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&"
    "gid=896757873"
)
termdefs = pd.read_csv(TERMDEF_URL, skiprows=2)

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

# Set @id to the value in column "datamodel" if it exists, otherwise to the same value as in datasettypes["@id"]
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

dmtable = DMTable.from_csv("datamodels.csv")


AGENTS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&"
    "gid=1445327120"
)
agents = pd.read_csv(AGENTS_URL)

#print("getting keywords")
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

# Get name of columns that can have more than one value from termdefs.
# Check the column SingleValue in termdefs.
# If False, then the value in column "Poperty"
list_columns = termdefs[
    termdefs["SingleValue"] == False  # pylint: disable=singleton-comparison
]["Tripper_keyword"].tolist()
# Add @id and @type to the list of columns that can have multiple values,
# because they can also be lists.
list_columns.extend(["@id", "@type"])
# Map properties to IRIs
property_to_iri = dict(zip(termdefs["Property"], termdefs["Tripper_keyword"]))


# Create the computatations documentation dataframe,
# and copy/move relevant columns from the software documentation dataframe.
ssbd_cols = [col for col in sw.columns if col.startswith("SSbD Assessment")]

activity_columns = [
    "inputDatasetType",
    "outputDatasetType",
] + ssbd_cols

comp = sw[activity_columns + ["title"]]
sw = sw.drop(columns=activity_columns)
# Remove the Ssbd columns in sw, these are deprecated
sw.drop(
    columns=[col for col in sw.columns if col.startswith("Ssbd")],
    inplace=True,
)



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
    merge_classes, axis=1, class_cols=chemicalclass_cols
)
sw.drop(columns=chemicalclass_cols, inplace=True)

# We have to decide how to handle Indicator, it is currently a class.
sw = sw.drop(columns=["indicator"])

sw["@type"] = "pink:Software"

expanded_sw = correct_pink_dataframes(sw, onto)
# A bit cumbersome to write file, I am sure there are better ways
expanded_sw.to_csv("sw_clean.csv", index=False)

swdocumentation = TableDoc.parse_csv(
    "sw_clean.csv",
    keywords=kw,
    context=context,
    # baseiri='https://w3id.org/pink/',
    prefixes=prefixes,
)

# Correct the computations documentation dataframe

print("PREPARING COMPUTATION TYPE DOCUMENTATION")
# Create a unique id (@id) for each activity in the comp dspreadsheet

comp["@id"] = comp.apply(
    lambda row: f"https://w3id.org/pink/activity/activity{row.name}", axis=1
)
# Add a column that defines that each activity is a prov:Activity and pink:Computation
# Reasoning tells us that a pink:Computation is a prov:Activity, but we add both for easier
# querying and to avoid relying on reasoning in the triplestore.
comp["@type"] = "owl:Class"

# Handle all the columns called SSbD Assessment ...
comp["subClassOf"] = comp.apply(
    lambda row: ["prov:Activity", "ssbd:Computation"]
    + merge_ssbd_assessments(row),
    axis=1,
)
comp.drop(
    columns=[col for col in comp.columns if col.startswith("SSbD")],
    inplace=True,
)

expanded_comp = correct_pink_dataframes(comp, onto)
expanded_comp.to_csv("comp_clean.csv", index=False)


compdocumentation = TableDoc.parse_csv(
    "comp_clean.csv", 
    keywords=kw, 
    context=context, 
    prefixes=prefixes
)

# Datasettype
print("PREPARING DATASETTYPE DOCUMENTATION")
# Drop indicator
datasettypes["@type"] = [["owl:Class"]] * len(datasettypes)

datasettypes = datasettypes.drop(columns=["indicator"])
expanded_datasettypes = correct_pink_dataframes(datasettypes, onto)
expanded_datasettypes.to_csv("datasettypes_clean.csv", index=False)
datasettypedocumentation = TableDoc.parse_csv(
    "datasettypes_clean.csv",
    keywords=kw,
    context=context,
    prefixes=prefixes,
)

# Save the data to the triplstore
# create the triplestore
ts = Triplestore("rdflib")



# Agents
print("PREPARING AGENT DOCUMENTATION")
agents["@type"] = [["prov:Agent"]] * len(agents)
agents = agents.drop(columns=["e-mail", "affiliation.name", "affiliation.id"])
#agents = agents[~agents["identifier"].isin(ts.subjects())]

agents_corrected = correct_pink_dataframes(agents, onto)
agents_corrected.to_csv("agents_clean.csv", index=False)
agentdocumentation = TableDoc.parse_csv(
    "agents_clean.csv",
    keywords=kw,
    context=context,
    prefixes=prefixes,
)



ad = agentdocumentation.save(ts)
sd = swdocumentation.save(ts)
cd = compdocumentation.save(ts)
dd = datasettypedocumentation.save(ts)


####
#dmtable = DMTable.from_csv("datamodels.csv")


####


# Get absolute current path
root_path = Path(__file__).parent.parent.resolve()
validation_path = root_path / "validation"
shacl_graph = load_shapes("https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/gh-pages/shacl/shapes.ttl")
shacl_graph.parse("https://raw.githubusercontent.com/ssbd-ontology/core/refs/heads/gh-pages/shacl/shapes-ssbd.ttl", format="turtle")


conforms, results_graph, report = shacl_validate(
    data_graph=ts.backend.graph,
    shacl_graph=shacl_graph,
    inference="rdfs",
    abort_on_first=False,
)


if not conforms:
    print("Validation failed.")
    print(report)

if conforms:
    print("Validation passed")
    print("unfortunately direct pushing is no longer possible")
    print("making a jsonld from my graph")
    ts.serialize("everything.ttl", format="turtle")
    
    graph = dict()

    graph['@context'] = ad['@context']
    graph['@graph'] = ad['@graph'] + sd['@graph'] + cd['@graph'] + dd['@graph']

    # Store the jsonlds for joh
    with open('everything.jsonld', 'wt') as f: 
        json.dump(graph, f, indent=2)



    # Connect to PINK KB
    #username = keyring.get_password("PINK_graphdb", "username")
    #password = keyring.get_password("PINK_graphdb", "password")

    #kb = Triplestore(
    #    backend="sparqlwrapper", 
    #    base_iri="https://graphdb.pink-project.eu/repositories/testing", 
    #    username=username, 
    #    password=password, 
    #    update_iri="https://graphdb.pink-project.eu/repositories/testing/statements",
    #    )
    #for s, p, o in ts.triples():
    #    kb.add((s, p, o))

    #print(search(kb))



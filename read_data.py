import re

from pyshacl import validate

from tripper import Triplestore, Literal
from tripper.datadoc import store, get_keywords, search, acquire, told, get_context
from tripper.datadoc.tabledoc import TableDoc
from pandas import read_csv
from pyld import jsonld
import json
import pandas as pd
import dateutil
from ontopy import get_ontology
from ontopy.exceptions import NoSuchLabelError
from validation.validate import validate_jsonld

def add_prefix(value, prefix='pink'):
    """Add prefix to value if it does not already have one and is not empty.
    If the value is a list, apply the function to each element in the list and return a new list.
    """
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    if isinstance(value, list):
        return [add_prefix(v, prefix) for v in value]
    value = str(value).strip()
    if (
        not value.startswith('http://') and 
        not value.startswith('https://') and 
        ':' not in value
        ):
        return ':'.join([prefix, value])
    return value

def correct_tier_level(value):
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    return value.strip().split(' ')[0]

def merge_classes(row, class_cols):
    '''
    Merge values from multiple class columns into a single list.
    '''
    values = []
    
    for col in class_cols:
        cell = row[col]
        
        if pd.notna(cell) and str(cell).strip() != "":
            # Split on comma
            parts = str(cell).split(',')
            
            # Clean whitespace and add
            cleaned = [p.strip() for p in parts if p.strip() != ""]
            values.extend(cleaned)
    
    return values

def split_to_list(value):
    '''
    Split value to a list on comma, semicolon, pipe, or space, 
    and clean whitespace. 
    Return None if empty or NaN.
    Return value as is if it is not a string (e.g. already a list).
    '''
    if not isinstance(value, str):
        return value  # Return as is if not a string
    if pd.isna(value) or str(value).strip() == "":
        return None  # Return None if empty or NaN
    # Split on comma, semicolon, pipe, or space
    parts = re.split(r'[,\s;|]+', value)
    # Clean whitespace and remove empty strings
    cleaned = [p.strip() for p in parts if p.strip() != ""]
    return cleaned

def expand_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand the dataframe: Any column whose values are lists
    will be expanded into multiple columns (all using the same header),
    with blanks where the lists were shorter.
    """
    parts = []
    for col in df.columns:
        is_list_col = df[col].apply(lambda v: isinstance(v, list)).any()
        if is_list_col:
            sub = pd.DataFrame(
                df[col].apply(lambda v: v if isinstance(v, list) and v else [None]).tolist()
            )
            sub.columns = [col] * sub.shape[1]
            parts.append(sub)
        else:
            parts.append(df[[col]])

    out = pd.concat(parts, axis=1)

    # clean the output (not the original df)
    out = out.map(lambda x: x.strip() if isinstance(x, str) else x)
    out = out.replace(r'^\s*$', '', regex=True).fillna('')

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
        if val.startswith("http://") or val.startswith("https://") or ":" in val:
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
                return val

        return val

    return df.map(process_value)

def correct_pink_dataframes(df, ontology):
    """
    Correct the pink dataframes by:
    - Adding prefixes to values in certain columns
    - Merging class columns into a single column
    - Splitting columns with multiple values into lists
    - Checking for URIs and replacing with IRIs from the ontology
    """
 
    df.rename(columns=property_to_iri, inplace=True)
    # remove rows with empty @id
    
    # Convert releaseDate to ISO format (YYYY-MM-DD)
    print(df.columns)
    if 'releaseDate' in df.columns:
        df['releaseDate'] = df['releaseDate'].apply(lambda x: dateutil.parser.parse(x).isoformat() if pd.notna(x) else None)

    # correct tier level
    if 'tierLevel' in df.columns:
        df['tierLevel'] = df['tierLevel'].apply(correct_tier_level)

    # Add prefixes to values
    if 'accessRights' in df.columns:
        df['accessRights'] = df['accessRights'].apply(add_prefix, prefix='rights')

    for col in ['tierLevel', '@id']:
        if col in df.columns:    
            df[col] = df[col].apply(add_prefix, prefix='pink')


    # Remove the all columns that have '(comment)' in their name
    # These are for the curators filling out the spreadsheet and should 
    # be looked at with them.
    df.drop(columns=[col for col in df.columns if '(comment)' in col], inplace=True)

    # Change possible lists to lists
    for col in set(list_columns).intersection(df.columns):
        df[col] = df[col].apply(split_to_list)
    
    expanded_df = expand_df(df)
    check_for_uris(expanded_df, ontology)
    return expanded_df


def validate_and_store_documentation(documentation, ts):
    """
    Validate the documentation and store it in the triplestore if valid.
    Otherwise print the validation report.
    """
    conforms = True
    for doc in documentation.asdicts():
        conforms, report = validate_jsonld(jsonld=doc)
        if not conforms:
            print(f"Validation failed for document with @id {doc.get('@id', 'unknown')}:")
            print(report)
            break
    print(f"Validation result: {'VALID' if conforms else 'INVALID'}")
    
    if conforms:
        documentation.save(ts)

# import the pink ontology for accessing labels and convert to IRIs (just before storing into the triplestore)
onto =  get_ontology('pink_annotation_schema.ttl').load()

# create the triplestore
ts = Triplestore('rdflib')

# Get data from Google Sheets
# Software documentation
sw_url = "https://docs.google.com/spreadsheets/d/1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&gid=1707023773"
sw = pd.read_csv(sw_url)

# Term definitions
termdef_url = "https://docs.google.com/spreadsheets/d/1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&gid=896757873"
termdefs = pd.read_csv(termdef_url, skiprows=2)

# Dataset documentation
datasettype_url = "https://docs.google.com/spreadsheets/d/1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&gid=1581267372"
datasettypes = pd.read_csv(datasettype_url)

# Get pink keywords
kw = get_keywords(theme=None)
kw.load_yaml('https://pink-project.github.io/PINK-annotation-schema/context/keywords.yaml', redefine='allow')

#context=get_context('https://pink-project.github.io/PINK-annotation-schema/context/pink_annotation_schema.jsonld')
context=get_context('context_corrected.jsonld')

# Get name of columns that can have more than one value from termdefs. Check the column SingleValue in termdefs. If False, then the value in column "Poperty"
list_columns = termdefs[termdefs['SingleValue'] == False]['Tripper_keyword'].tolist()
# Add @id and @type to the list of columns that can have multiple values, because they can also be lists.
list_columns.extend(['@id', '@type'])
# Map properties to IRIs
property_to_iri = dict(zip(termdefs['Property'], termdefs['Tripper_keyword']))


# Create the computatations documentation dataframe, and copy/move relevant columns from the software documentation dataframe.
activity_columns = ['inputDatasetType', 'outputDatasetType',
                    'SsbdDimension', 'SsbdSubDimension', 'SsbdSubSubDimension']

comp = sw[activity_columns+['title']]
sw = sw.drop(columns=activity_columns)


# Correct sowtare documentation dataframe

# Clean up the chemicalClass, which is currently in three columns for easier annotation in the spreadsheet.
chemicalclass_cols = [
    'chemicalClass[by type]',
    'chemicalClass[by size]',
    'chemicalClass[by functionality]'
]
sw['chemicalClass'] = sw.apply(merge_classes, axis=1, class_cols=chemicalclass_cols)
sw.drop(columns=chemicalclass_cols, inplace=True)

# We have to decide how to handle Indicator, it is currently a class.
sw = sw.drop(columns=["indicator"])

expanded_sw = correct_pink_dataframes(sw, onto)
# A bit cumbersome to write file, I am sure there are better ways
expanded_sw.to_csv('sw_clean.csv', index=False)  

swdocumentation = TableDoc.parse_csv(
        'sw_clean.csv',
        keywords=kw,
        context=context,
        #baseiri='https://w3id.org/pink/',
        prefixes={'mw': 'https://modelwave.it/ontology/',
                  'rights': 'http://publications.europa.eu/resource/authority/access-right/',
                  'datasettype': 'https://w3id.org/pink/datasettype/'}
        )

# Validate and save software documentation to triplestore
validate_and_store_documentation(swdocumentation, ts)


# Correct the computations documentation dataframe 

# Create a unique id (@id) for each activity in the comp dspreadsheet
comp['@id'] = comp.apply(lambda row: f"https://w3id.org/pink/activity/{row.name}", axis=1)
# Add a column that defines that each activity is a prov:Activity
comp['@type'] = 'prov:Activity'

# Add alle values under SsbdDimension, SsvbSubDimension and SsbdSubSubDimension 
# into the column '@type' as list.
def merge_ssbd_dimensions(row):
    values = []
    
    for col in ['SsbdDimension', 'SsbdSubDimension', 'SsbdSubSubDimension']:
        cell = row[col]
        
        if pd.notna(cell) and str(cell).strip() != "":
            # Split on comma
            parts = str(cell).split(',')
            
            # Clean whitespace and add
            cleaned = ['pink:'+p.strip() for p in parts if p.strip() != ""]
            values.extend(cleaned)
    
    return values

comp['@type'] = comp.apply(lambda row: ['prov:Activity'] + merge_ssbd_dimensions(row), axis=1)

# Remove the Ssbd columns
comp.drop(columns=[col for col in comp.columns if col.startswith('Ssbd')], inplace=True)


expanded_comp = correct_pink_dataframes(comp, onto)
expanded_comp.to_csv('comp_clean.csv', index=False)


compdocumentation = TableDoc.parse_csv(
        'comp_clean.csv',
        keywords=kw,
        context=context,
        prefixes={'mw': 'https://modelwave.it/ontology/', 'datasettype': 'https://w3id.org/pink/datasettype/'}
        )

validate_and_store_documentation(compdocumentation, ts)


# Datasettype
#Remove all columns starting with 'Datum' (these go into the datamodel)
datasettypes = datasettypes.drop(columns=[col for col in datasettypes.columns if col.startswith('datum')])
# Remove Unamed columns
datasettypes = datasettypes.loc[:, ~datasettypes.columns.str.contains('^Unnamed')]


# Drop indicator
datasettypes = datasettypes.drop(columns=["indicator"])
expanded_datasettypes = correct_pink_dataframes(datasettypes, onto)
expanded_datasettypes.to_csv('datasettypes_clean.csv', index=False)
datasettypedocumentation = TableDoc.parse_csv(
        'datasettypes_clean.csv',
        keywords=kw,
        context=context,
        prefixes={'mw': 'https://modelwave.it/ontology/', 'datasettype': 'https://w3id.org/pink/datasettype/'}
        )
validate_and_store_documentation(datasettypedocumentation, ts)
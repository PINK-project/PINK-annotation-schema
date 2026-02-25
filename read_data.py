import re

from pyshacl import validate

from tripper import Triplestore, Literal
from tripper.datadoc import store, get_keywords, search, acquire, told
from tripper.datadoc.tabledoc import TableDoc
from pandas import read_csv
from pyld import jsonld
import json
import pandas as pd
import dateutil
from ontopy import get_ontology
from ontopy.exceptions import NoSuchLabelError

# in column 'accessRights', add 'rights:' prefix to all values that are not empty and that do not have a prefix already.
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

def expanded_df(df: pd.DataFrame) -> pd.DataFrame:
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
            if not (val.startswith("http://") or val.startswith("https://")):
                lookup_val = val.split(":", 1)[1]

            try:
                term = ontology[lookup_val]
                print(f"Replacing {val} with IRI: {term.iri}")
                return term.iri
            except NoSuchLabelError:
                print(f"Warning: {val} not found in ontology")
                return val

        return val

    return df.map(process_value)


# import the pink ontology for accessing labels and convert to IRIs (just before storing into the triplestore)
onto =  get_ontology('pink_annotation_schema.ttl').load()
# Get data from Google Sheets
# Software documentation
sw_url = "https://docs.google.com/spreadsheets/d/1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&gid=1707023773"
sw = pd.read_csv(sw_url)

# Term definitions
termdef_url = "https://docs.google.com/spreadsheets/d/1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU/export?format=csv&gid=896757873"
termdefs = pd.read_csv(termdef_url, skiprows=2)

# Get pink keywords
kw = get_keywords(theme=None)
kw.load_yaml('https://pink-project.github.io/PINK-annotation-schema/context/keywords.yaml', redefine='allow')

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

# Correct column names
# Clean up the chemicalClass, which is currently in three columns for easier annotation in the spreadsheet.
chemicalclass_cols = [
    'chemicalClass[by type]',
    'chemicalClass[by size]',
    'chemicalClass[by functionality]'
]
sw['chemicalClass'] = sw.apply(merge_classes, axis=1, class_cols=chemicalclass_cols)
sw.drop(columns=chemicalclass_cols, inplace=True)

# Remove the all columns that have '(comment)' in their name
# These are for the curators filling out the spreadsheet and should 
# be looked at with them.
sw.drop(columns=[col for col in sw.columns if '(comment)' in col], inplace=True)

# We have to decide how to handle Indicator, it is currently a class.
sw = sw.drop(columns=["indicator", 
                      ])


# Convert releaseDate to ISO format (YYYY-MM-DD)
sw['releaseDate'] = sw['releaseDate'].apply(lambda x: dateutil.parser.parse(x).isoformat() if pd.notna(x) else None) 

# Rename some columns to match the ontology
#sw.rename(columns={"modelType": "implementsModel", "identifier": "@id"}, inplace=True)

# Correct the values 
# Change lists to lists
# Change all haeders according to the property_to_iri mapping
sw.rename(columns=property_to_iri, inplace=True)
for col in set(list_columns).intersection(sw.columns):
    sw[col] = sw[col].apply(split_to_list)
# Add prefixes to values
sw['accessRights'] = sw['accessRights'].apply(add_prefix, prefix='rights')

sw['tierLevel'] = sw['tierLevel'].apply(correct_tier_level)
sw['tierLevel'] = sw['tierLevel'].apply(add_prefix, prefix='pink')

# Add @id because tripper does not accept dcterms:identifier as identifier for some reason.
sw['@id'] = sw['@id'].apply(add_prefix, prefix='pink')



# A bit cumbersome to write file, I am sure there are better ways
expanded_sw = expanded_df(sw)
check_for_uris(expanded_sw, onto)



expanded_sw.to_csv('sw_clean.csv', index=False)  


swdocumentation = TableDoc.parse_csv(
        'sw_clean.csv',
        keywords=kw,
        #baseiri='https://w3id.org/pink/',
        prefixes={'mw': 'https://modelwave.it/ontology/','rights': 'http://publications.europa.eu/resource/authority/access-right/'}
        )

# Save software documentation to triplestore

ts = Triplestore('rdflib')
v = swdocumentation.save(ts)
#v = told(swdocumentation.asdicts(), keywords=kw)

# Save the computational entities as activities
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

print(comp['@type']) 

# Remove the Ssbd columns
comp.drop(columns=[col for col in comp.columns if col.startswith('Ssbd')], inplace=True)

# Change all headers according to the property_to_iri mapping

comp.rename(columns=property_to_iri, inplace=True)
for col in set(list_columns).intersection(comp.columns):
    comp[col] = comp[col].apply(split_to_list)
 
# A bit cumbersome to write file, I am sure there are better ways
expanded_comp = expanded_df(comp)

corrected_iris_comp = check_for_uris(expanded_comp, onto)

corrected_iris_comp.to_csv('comp_clean.csv', index=False)


compdocumentation = TableDoc.parse_csv(
        'comp_clean.csv',
        keywords=kw,
        prefixes={'mw': 'https://modelwave.it/ontology/'}
        )

# Save software documentation to triplestore
compdocumentation.save(ts)


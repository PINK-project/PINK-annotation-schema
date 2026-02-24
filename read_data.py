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

def export_expanded_csv(df: pd.DataFrame, path: str) -> None:
    """
    Export df to CSV at `path`. Any column whose values are lists
    will be expanded into multiple columns (all using the same header),
    with blanks where the lists were shorter.
    """
    parts = []
    for col in df.columns:
        print('processing column:', col)
        # detect if this column has any list entries
        is_list_col = df[col].apply(lambda v: isinstance(v, list)).any()
        print('is list column:', is_list_col)
        if is_list_col:
            # convert each row's list to a row in a small DF
            sub = pd.DataFrame(
                df[col].apply(
                    lambda v: v if isinstance(v, list) and len(v) > 0 else [None]
                ).tolist()
            )
            # rename all its columns to the original header
            sub.columns = [col] * sub.shape[1]
            parts.append(sub)
        else:
            # just take the series as a one-column DF
            parts.append(df[[col]])
    # remove all values that are empty lists or strings with only whitespace
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    # Replace empty strings and NaN with ""
    df = df.replace(r'^\s*$', '', regex=True)
    df = df.fillna('')
    # concatenate side by side
    expanded = pd.concat(parts, axis=1)
    print('expanded columns:', expanded.columns)
    print('expanded head:', expanded.head())
    expanded.to_csv(path, index=False)




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
list_columns = termdefs[termdefs['SingleValue'] == False]['IRI'].tolist()
# Add @id and @type to the list of columns that can have multiple values, because they can also be lists.
list_columns.extend(['@id', '@type'])
# Map properties to IRIs
property_to_iri = dict(zip(termdefs['Property'], termdefs['IRI']))

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
sw['dcterms:accessRights'] = sw['dcterms:accessRights'].apply(add_prefix, prefix='rights')

sw['pink:tierLevel'] = sw['pink:tierLevel'].apply(correct_tier_level)
sw['pink:tierLevel'] = sw['pink:tierLevel'].apply(add_prefix, prefix='pink')

# Add @id because tripper does not accept dcterms:identifier as identifier for some reason.
sw['@id'] = sw['dcterms:identifier'].apply(add_prefix, prefix='pink')

# A bit cumbersome to write file, I am sure there are better ways

export_expanded_csv(sw, 'sw_clean.csv')  


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

print(comp.head())
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
 

# Remove the Ssbd columns
comp.drop(columns=[col for col in comp.columns if col.startswith('Ssbd')], inplace=True)

# Change all haeders according to the property_to_iri mapping
comp.rename(columns=property_to_iri, inplace=True)
for col in set(list_columns).intersection(comp.columns):
    print('col that may be listcol:', col)
    comp[col] = comp[col].apply(split_to_list)
 
print('a')
print(comp.head())
print('b')
# A bit cumbersome to write file, I am sure there are better ways
export_expanded_csv(comp, 'comp_clean.csv')


compdocumentation = TableDoc.parse_csv(
        'comp_clean.csv',
        keywords=kw,
        prefixes={'mw': 'https://modelwave.it/ontology/'}
        )

# Save software documentation to triplestore
compdocumentation.save(ts)



'''
data_graph = "some-data.ttl"
shacl_graph = "pink_shacl.ttl"
ont_graph = "pink_annotation_schema.ttl"

r = validate(data_graph,
      shacl_graph=shacl_graph,
      ont_graph=ont_graph,
      inference='rdfs',
      abort_on_first=False,
      allow_infos=False,
      allow_warnings=False,
      meta_shacl=False,
      advanced=False,
      js=False,
      debug=False)
conforms, results_graph, results_text = r
'''

"""
Script parses a user provided spreadsheet with annotations for software documentation.

It accepts Goole spreadsheets and validates data before it is saved to a csv file.

The csv files are then used in the next step to create triples and save them to the triplestore.
"""

import sys
import pandas as pd
import openpyxl
from styleframe import StyleFrame, Styler
import numpy as np
import argparse
import re
import json

import ontopy
import orcid
import requests
import datetime
import dateutil.parser 

def cleanDF(df):
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace("-", "").replace("", pd.NA).fillna(value=pd.NA)
    return(df)

#---------- Setup for validation: profile definition, known prefixes and error table ----------

# Create an empty error table to collect warnings, errors and information on automaticly applied modifications during the parsing and validation of the spreadsheet.
def create_error_table():
    return pd.DataFrame(columns=['row', 'column', 'type', 'message'])

def add_error(error_table, row, column, error_type, message):
    new_error = pd.DataFrame({'row': [row], 'column': [column], 'type': [error_type], 'message': [message]})
    return pd.concat([error_table, new_error], ignore_index=True)

# Create a simple profile of the annotations for software as a pandas df
# Possible datatypes are: 
#       string 
#       IRI
#       List[string]
#       boolean
#       date
#       SSbDCore (entry exist in SSbD Core ontology)
#       OrgIRI (ROR or ORCID identifier)
#       PersonIRI (ORCID identifier)

PREFIXES: dict[str, str] = {
    "mw": "https://modelwave.it/",
    "rights": "http://publications.europa.eu/resource/authority/access-right/",
    "datasettype": "https://pink-project.eu/datasettype/",
    "qsar": "https://pink-project.eu/qsar/",
    "pink": "https://pink-project.eu/",
    "pinkag": "https://pink-project.eu/agent/",
    "empa": "https://empa.ch/",
    "empadm": "https://empa.ch/datamodel/",
    "oboowl": "http://www.geneontology.org/formats/oboInOwl#",
    "obo": "http://purl.obolibrary.org/obo/",
    "chemowl": "http://www.semanticweb.org/ontologies/cheminf.owl#",
    "cheminf": "http://semanticscience.org/resource/",
    "omics": "http://pink-project.eu/omics/",
    "ssbd": "https://w3id.org/ssbd/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "emmo": "https://w3id.org/emmo/hume#"
}

def create_know_datatype_table():
    columns = [['identifier', 'string', 'mandatory'], # should become an instance of a class?
               ['title', 'string', 'mandatory'],
               ['description', 'string', 'optional'],
               ['keyword', 'List[string]', 'optional'],
               ['inputDatasetType', 'string', 'optional'],
               ['outputDatasetType', 'string', 'optional'],
               ['outputsIndicator', 'string', 'optional'],
               ['inTierLevel', 'List[SSbDclass]', 'recommended'], # should become mandatory
               ['SSbD Assessment level 1', 'SSbDclass', 'mandatory'],
               ['SSbD Assessment level 2', 'List[SSbDclass]', 'recommended'],
               ['SSbD Assessment level 3', 'List[SSbDclass]', 'optional'],
               ['documentation', 'IRI', 'optional'],
               ['accessURL', 'IRI', 'optional'],
               ['downloadURL', 'IRI', 'optional'],
               ['modelType', 'List[SSbDinstance]', 'optional'],
               ['hasAPI', 'boolean', 'mandatory'],
               ['hasGUI', 'boolean', 'mandatory'],
               ['accessRights', 'IRI', 'mandatory'],
               ['rightsHolder', 'List[OrgIRI]', 'optional'],
               ['license', 'IRI', 'optional'],
               ['creator', 'List[OrgIRI]', 'mandatory'],
               ['releaseDate', 'date', 'optional'],
               ['priorRelease', 'date', 'optional'],
               ['version', 'string', 'optional'],
               ['chemicalClass[by type]', 'List[SSbDclass]', 'recommended'], # might become mandatory in the future
               ['chemicalClass[by size]', 'List[SSbDclass]', 'recommended'], # might become mandatory in the future
               ['chemicalClass[by functionality]', 'List[SSbDclass]', 'optional'],
               ['curator', 'List[PersonIRI]', 'recommended']] # should become mandatory soon
    
    return(pd.DataFrame(columns=['column_name', 'datatype', 'condition'], data=columns))


#---------- Input validation ----------


# Convert a value to an IRI if it starts with a known prefix.
# If the value is empty or NaN, return it as is.
# Convert a value to an IRI if it starts with a known prefix.
# If the value is empty or NaN, return it as is.
def convert_to_iri(value, prefixes=PREFIXES):
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    if value.startswith("http://") or value.startswith("https://"):
        return value  # Return as is if full IRI
    value = str(value).strip()
    for prefix, iri in prefixes.items():
        if value.startswith(prefix + ":"):
            return value.replace(prefix + ":", iri)
    return None

def replace_short_prefixes(column, column_name, prefixes, error_table):
    for i, value in column.items():
        if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
           column[i] = value
        elif isinstance(value, list):
            new_value = []
            for v in value:
                new_v = convert_to_iri(v, prefixes)
                if (new_v is not None):
                    if (new_v != v):
                        error_table = add_error(error_table, i, column_name, "Info", f'Term {v} was resolved to full IRI {new_v}')
                    new_value.append(new_v)
                else:
                    error_table = add_error(error_table, i, column_name, "Warning", f'Prefix in {v} is unknown.')
                    new_value.append(v)
            column[i] = new_value
        else:
            new_v = convert_to_iri(value, prefixes)
            if (new_v is not None):
                if (new_v != value):
                    error_table = add_error(error_table, i, column_name, "Info", f'Term {value} was resolved to full IRI {new_v}')
                column[i] = new_v
            else:
                error_table = add_error(error_table, i, column_name, "Warning", f'Prefix in {value} is unknown.')
                column[i] = value

    return(column, error_table)

# Add prefix to value if it does not already have one and is not empty.
# If the value is a list, apply the function to each element in the list and return a new list.
def add_prefix(value, prefix="pink"):
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

# Correct the value by removing everything after the first space.
# For pink, this is done specifically in the tierLevel column, as some curators desired explanations on the tier level, which should be removed.
def remove_extra_text(value):
    if isinstance(value, list):
        return [remove_extra_text(v) for v in value]
    if pd.isna(value) or str(value).strip() == "":
        return value  # Return as is if empty or NaN
    return value.strip().split(" ")[0]


#currently only ORCIDs are supported as PersonIRI, but this can be extended to other identifiers in the future.
def validate_orcid(value, row, column, credentials, error_table):
    if (('orcid' not in credentials.keys()) or ('api' not in credentials["orcid"].keys())):
        r = re.compile('https://orcid.org/.{4}-.{4}-.{4}-.{4}')
        if len(value) == 37 and r.match(value):
            error_table = add_error(error_table, row, column, 'Info', f'{value} has correct format but could not be checked further because of missing credentials to ORCID API.') 
        else: 
            error_table = add_error(error_table, row, column, 'Error', f'Invalid ORCID format in list: {value}. Expected format: https://orcid.org/XXXX-XXXX-XXXX-XXXX') 

    try:
        summary = credentials["orcid"]['api'].read_record_public(value.replace("https://orcid.org/", ""), 'person', credentials["orcid"]['token'])
        if summary is None:
            error_table = add_error(error_table, row, column, 'Warning', f'No information for ORCID {value}.')
        else:
           error_table = add_error(error_table, row, column, 'Info', f'ORCID {value} is valid: {summary["name"]['given-names']['value']} {summary["name"]['family-name']['value']}.')
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Error validating ORCID {value}: {e}')

    return error_table


def validate_PersonIRI(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.startswith("https://orcid.org/"):
                error_table = validate_orcid(item, row, column, credentials, error_table)
            else:
                error_table = add_error(error_table, row, column, 'Error', f'Invalid PersonIRI format in list: {item} - {value}. Expected format: https://orcid.org/XXXX-XXXX-XXXX-XXXX')

    else:
        if isinstance(value, str) and value.startswith("https://orcid.org/"):
            error_table = validate_orcid(value, row, column, credentials, error_table)
        else:
            error_table = add_error(error_table, row, column, 'Error', f'Invalid PersonIRI format: {value}. Expected format: https://orcid.org/XXXX-XXXX-XXXX-XXXX')
 
    return error_table

#currently only ROR IDs are supported as OrgIRI, but this can be extended to other identifiers in the future.
def validate_ror(value, row, column, credentials, error_table):
    try:
        query = f"https://api.ror.org/v2/organizations/{value.replace('https://ror.org/', '')}"
        response = requests.get(query)
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Error validating ROR ID {value}: {e}')
        return error_table

    if response.status_code == 200:
        for name in response.json()["names"]:
            if "ror_display" in name["types"]:
                error_table = add_error(error_table, row, column, 'Info', f'ROR ID {value} is valid: {name["value"]}')
                break
    else:
        error_table = add_error(error_table, row, column, 'Error', f'ROR ID {value} is invalid: {response.status_code}')

    return error_table

def validate_OrgIRI(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.startswith("https://ror.org/"):
                error_table = validate_ror(item, row, column, credentials, error_table)
            elif isinstance(item, str) and item.startswith("https://orcid.org/"):
                error_table = validate_orcid(item, row, column, credentials, error_table)
            else:
                error_table = add_error(error_table, row, column, 'Error', f'Invalid OrgIRI format in list: {item} - {value}. Expected format: https://ror.org/XXXXXXXXXX or https://orcid.org/XXXX-XXXX-XXXX-XXXX')

    else:
        if isinstance(value, str) and value.startswith("https://ror.org/"):
            error_table = validate_ror(value, row, column, credentials, error_table)
        elif isinstance(value, str) and value.startswith("https://orcid.org/"):
            error_table = validate_orcid(value, row, column, credentials, error_table)
        else:
            error_table = add_error(error_table, row, column, 'Error', f'Invalid OrgIRI format: {value}. Expected format: https://ror.org/XXXXXXXXXX or https://orcid.org/XXXX-XXXX-XXXX-XXXX')
 
    return error_table

def validate_IRIexists(value, row, column, credentials, error_table):
    try:
        query = f"https://api.ror.org/v2/organizations/{value.replace('https://ror.org/', '')}"
        response = requests.get(value)
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Error accessing IRI {value}: {e}')
        return error_table

    if response.status_code < 400:
        error_table = add_error(error_table, row, column, 'Info', f'URL {value} is accessible: {response.status_code}')
    else:
        error_table = add_error(error_table, row, column, 'Error', f'URL {value} is not accessible: {response.status_code}')

    return error_table
   

def validate_IRI(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and (item.startswith("https:") or item.startswith("http:")):
                error_table = validate_IRIexists(item, row, column, credentials, error_table)
            else:
                error_table = add_error(error_table, row, column, 'Error', f'Invalid IRI format in list: {item} - {value}. Expected format: XXXX:XXXXX')

    else:
        if isinstance(value, str) and (value.startswith("https:") or value.startswith("http:")):
            error_table = validate_IRIexists(value, row, column, credentials, error_table)
        else:
            error_table = add_error(error_table, row, column, 'Error', f'Invalid IRI format or not resolvable: {value}. Expected format: XXXX:XXXXX')
    return error_table


# Check terms exist in SSbD ontology
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

# Do the analysis of the value to find if it corresponds to an IRI in the ontology.
# This is done only because people do not want to use the IRIs directly but prefer to use rdfs:label
def process_value(val, ontology, prefixes):
    if not isinstance(val, str):
        return None

    val = val.strip()
    if not val:
        return None

    # Detect URI-like values with prefixes corresponding to the chosen ontology
    lookup_val = val
    if ":" not in lookup_val:   # if no prefix is given, search find IRI by rdfs:label
        for candidate in case_variations(lookup_val.strip()):
            try:
                term = ontology.get_by_label(candidate)
                return term.iri
            except (ontopy.exceptions.NoSuchLabelError, AttributeError):
                pass
    else: 
        for prefix in prefixes:
            if lookup_val.startswith(prefix):
                lookup_val = convert_to_iri(lookup_val)
                if lookup_val is None: 
                    break
                try:
                    term = ontology.get_by_label(lookup_val)
                    return term.iri
                except (ontopy.exceptions.NoSuchLabelError, AttributeError):
                    pass
                break
    
    return None


def retrieve_IRI_from_ontology(column, column_name, ontology, prefixes, error_table):
    for i, value in column.items():
        if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
           column[i] = value
        elif isinstance(value, list):
            new_value = []
            for v in value:
                new_v = process_value(v, ontology, prefixes)
                if (new_v is not None):
                    if (new_v != v):
                        error_table = add_error(error_table, i, column_name, "Info", f'Term {v} is in ontology and was resolved to full IRI {new_v}')
                    new_value.append(new_v)
                else:
                    if any(iter(map(v.startswith, prefixes)))==True:
                        error_table = add_error(error_table, i, column_name, "Warning", f'Term {v} was not found in ontology.')
                    else:
                        error_table = add_error(error_table, i, column_name, "Warning", f'Prefix of {v} is not part of ontology.')
                    new_value.append(v)
            column[i] = new_value
        else:
            new_v = process_value(value, ontology, prefixes)
            if (new_v is not None):
                if (new_v != value):
                    error_table = add_error(error_table, i, column_name, "Info", f'Term {value} is in ontology and was resolved to full IRI {new_v}')
                column[i] = new_v
            else:
                if any(iter(map(value.startswith, prefixes)))==True:
                    error_table = add_error(error_table, i, column_name, "Warning", f'Term {value} was not found in ontology.')
                else:
                    error_table = add_error(error_table, i, column_name, "Warning", f'Prefix of {value} is not part of ontology.')
                column[i] = value

    return(column, error_table)


def correct_boolean(row, column_name):
    if isinstance(row[column_name], str):
        if ("yes"==row[column_name].lower().strip()):
            return pd.Series({column_name: True, \
                                'row': row.name,\
                                'column': column_name,\
                                'type': 'Info',\
                                'message': 'String \'yes\' was replaced by bool \'True\'.'}) 

        elif ("no"==row[column_name].lower().strip()):
            return pd.Series({column_name: False, \
                                'row': row.name,\
                                'column': column_name,\
                                'type': 'Info',\
                                'message': 'String \'no\' was replaced by bool \'False\'.'}) 

        else:
            return pd.Series({column_name: row[column_name], \
                                'row': row.name,\
                                'column': column_name,\
                                'type': 'Error',\
                                'message': f'String \'{row[column_name]}\' cannot be translated into a valid boolean type.'}) 
    else:
        return pd.Series({column_name: row[column_name], \
                                'row': None,\
                                'column': None,\
                                'type': None,\
                                'message': None}) 

def validate_boolean(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, bool):
                error_table = add_error(error_table, row, column, 'Error', f': Entry \'{item}\' is not of type boolean.')

    else:
        if not isinstance(value, bool):
            error_table = add_error(error_table, row, column, 'Error', f'Entry \'{value}\' is not of type boolean.')
    return error_table


def translate_strings_to_dates(row, column_name):
    if isinstance(row[column_name], str):
        try:
            date_obj = dateutil.parser.parse(row[column_name])
        except Exception as e:
            return pd.Series({column_name: row[column_name], \
                                'row': row.name,\
                                'column': column_name,\
                                'type': 'Error',\
                                'message': f'String \'{row[column_name]}\' cannot be translated into datetime: {e}.'}) 
        
        return pd.Series({column_name: date_obj, \
                                'row': row.name,\
                                'column': column_name,\
                                'type': 'Info',\
                                'message': f'String \'{row[column_name]}\' was translated into datetime \'{date_obj}\'.'}) 
    else:
        return pd.Series({column_name: row[column_name], \
                                'row': None,\
                                'column': None,\
                                'type': None,\
                                'message': None}) 


def validate_date(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, datetime.date):
                error_table = add_error(error_table, row, column, 'Error', f': Entry {item} is not of type datetime.')

    else:
         if not isinstance(value, datetime.date):
            error_table = add_error(error_table, row, column, 'Error', f'Entry {value} is not of type datetime.')
    return error_table


#----------------------------------------- Main ----------------------------------

def main():
    error_table = create_error_table()
    profile_table = create_know_datatype_table()

# PINK KB Resources Google Sheet is used as default input, but the user can specify a different Google Sheet or an Excel file with the same structure.
# If the -i flag is used, then an Excel file is used instead of the Google Sheet (standard Google Sheet or the one specified with the -I flag).

    parser = argparse.ArgumentParser(description='Reads and validates software annotations')
    parser.add_argument("-I", help="ID of the Google sheet, e.g. 1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU for the PINK KB Resources", dest="input_IRI", default="1o1buVRFL5wIrFxGDG6Oo7EDnA7dgxxoZRpa2JpwX0BU")
    parser.add_argument("-S", help="ID of the software tab in the Google sheet, e.g. 1707023773 for the PINK KB Resources", dest="input_sheet", default="1707023773")
    parser.add_argument("-i", help="Name of the Input Excel file", dest="input_file", default="")
    parser.add_argument("-s", help="Name of the software tab in the Excel file", dest="input_tab", default="")
    parser.add_argument("-o", help="Name of the output csv file", dest="output_file", default="output/sw_clean.csv")
    parser.add_argument("-e", help="Name of the csv file with software failing the validation", dest="failed_file", default="output/sw_failed.csv")
    parser.add_argument("-l", help="Name of the log file documenting errors and warnings", dest="log_file", default="output/sw_log.xlsx")
    parser.add_argument("-c", help="Name of the file with web service credentials", dest="credentials_file", default="credentials.json")
    args = parser.parse_args()

    print(f"\n --- Software annotation validation script {sys.argv[0]} ---")



#---------- Read Excel or Google Sheet with software annotations ----------

    if (args.input_file == ""):
        print(f"\nUsing \n\tinput IRI: {args.input_IRI}\n\tinput sheet: {args.input_sheet}\n\tcorrect entries: {args.output_file}\n\tfailed entries: {args.failed_file}\n\tlog file: {args.log_file}\n")

        googleSW_URL = "https://docs.google.com/spreadsheets/d/"+args.input_IRI+"/export?format=csv&gid="+args.input_sheet
        try:
            software_table = pd.read_csv(googleSW_URL)
        except Exception as e:
            print(f"\nError reading Google Sheet: {e}\n")
            return
    else:
        print(f"\nUsing \n\tinput file: {args.input_file}\n\tinput tab: {args.input_tab}\n\tcorrect entries: {args.output_file}\n\tfailed entries: {args.failed_file}\n\tlog file: {args.log_file}\n")

        try:
            if args.input_tab == "":
                software_table = pd.read_excel(args.input_file)
            else:
                software_table = pd.read_excel(args.input_file, sheet_name=args.input_tab)
        except Exception as e:
            print(f"\nError reading Excel file: {e}\n")
            return

#    software_table = software_table.head(2)  # Limit to first X rows for testing purposes, remove this line for full processing

    try:
        ssbd = ontopy.get_ontology("https://ssbd-ontology.github.io/core/core-inferred.ttl").load()
    except Exception as e:
            print(f"\nError reading SSbD Core Ontology: {e}\n")
            return

    try:
        credentials = json.load(open(args.credentials_file))
    except Exception as e:
        print(f"\nError reading credentials file: {e}\n")
        return

    print(f"\nUsing credentials from {args.credentials_file}: {credentials}\n")

    if "orcid" in credentials:
        credentials["orcid"]['api'] = orcid.PublicAPI(credentials["orcid"]['client_id'], credentials["orcid"]['client_secret'], sandbox=False) 
        credentials["orcid"]['token'] = credentials["orcid"]['api'].get_search_token_from_orcid()
    
    software_table = cleanDF(software_table)
    #print(software_table)



#---------- Validate the columns in the software table against the profile table ----------

# Script exits if mandatory columns are not present and provides the error messages in the error file.

    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        datatype = row['datatype']
        condition = row['condition']

        if column_name not in software_table.columns:
            if condition == 'mandatory':
                error_table = add_error(error_table, None, column_name, 'Error', f'Mandatory Column {column_name} is missing from the software table.')
            elif condition == 'recommended':
                error_table = add_error(error_table, None, column_name, 'Warning', f'Recommended Column {column_name} is missing from the software table.')
            else:
                error_table = add_error(error_table, None, column_name, 'Info', f'Optional Column {column_name} is missing from the software table.')

    if (not error_table[error_table['type'] == 'Error'].empty):
        print("\nErrors found in the software table. Please check the log file for details.")
        print(error_table)
        error_table.to_csv(args.log_file, index=False)
        return



#---------- Modify input based on simplified user input ----------

# Simplifications include
# - semicolon-separated lists
# - use of prefixes for IRIs (e.g. "pink:software" instead of "https://pink-project.eu/software")
# - no prefix in columns SSbD Assessment levels and, accessRights
# - Yes/No for boolean columns
#  
    # Transform columns with list-like values (semicolon-separated) into actual lists
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in software_table.columns:
            if row['datatype'].startswith('List'):
                software_table[column_name] = software_table[column_name].apply(
                    lambda x: str(x).replace(',', ';') if (pd.notna(x) and (';' not in str(x))) else x
                )
                software_table[column_name] = software_table[column_name].apply(
                    lambda x: [item.strip() for item in str(x).split(';')] if pd.notna(x) else x
                )

    # Transforms yes/no to bool
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in software_table.columns:
            if row['datatype'] == 'boolean':
                valid = software_table.apply(correct_boolean, column_name=column_name, axis=1, result_type='expand')
                software_table[column_name] = valid.pop(column_name)
                valid.dropna(how='all', inplace=True)
                if error_table.empty:
                    error_table = valid
                elif not valid.empty:
                    error_table = pd.concat([error_table, valid])

    # Checks and harmonises dates
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in software_table.columns:
            if row['datatype'] == 'date':
                valid = software_table.apply(translate_strings_to_dates, column_name=column_name, axis=1, result_type='expand')
                software_table[column_name] = valid.pop(column_name)
                error_table = pd.concat([error_table, valid.dropna(how='all')])


    # Add prefix to specific columns and remove extra content
    if "accessRights" in software_table.columns:
        software_table["accessRights"] = software_table["accessRights"].apply(add_prefix, prefix="rights")

    if "inTierLevel" in software_table.columns:
        software_table["inTierLevel"] = software_table["inTierLevel"].apply(remove_extra_text)

    # Check ontology - currently only SSbD including the relevant EMMO parts
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if (column_name in software_table.columns) and ("SSbD" in row['datatype']):
            software_table[column_name], error_table = retrieve_IRI_from_ontology(software_table[column_name].copy(deep=True), column_name, ssbd, ["ssbd:", "emmo:", "https://w3id.org/ssbd/", "https://w3id.org/emmo/"], error_table)

    # Replace known prefixes
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in software_table.columns and ("IRI" in row['datatype']):
            software_table[column_name], error_table = replace_short_prefixes(software_table[column_name].copy(deep=True), column_name, PREFIXES, error_table)


#---------- Validate the individual software entries against the profile table ----------
# 

    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        datatype = row['datatype']
        condition = row['condition']

        if datatype == 'PersonIRI' or datatype == 'List[PersonIRI]':
            validation_function = validate_PersonIRI
        elif datatype == 'OrgIRI' or datatype == 'List[OrgIRI]':
            validation_function = validate_OrgIRI
        elif datatype == 'IRI' or datatype == 'List[IRI]':
            validation_function = validate_IRI
        elif "SSbD" in datatype: # to be implemented
            validation_function = None
        elif datatype == 'boolean':
            validation_function = validate_boolean
        elif datatype == 'date':
            validation_function = validate_date
        else: 
            validation_function = None
        
        for j, row2 in software_table.iterrows():
            if condition == 'mandatory' or condition == 'recommended':
                if not isinstance(row2[column_name], list) and (pd.isna(row2[column_name]) or (isinstance(row2[column_name], float) and np.isnan(row2[column_name]))):
                    type_of_error = 'Error' if condition == 'mandatory' else 'Warning'
                    error_table = add_error(error_table, j, column_name, type_of_error, f'{condition.capitalize()} field {column_name} is missing.')
                    continue
            
            if validation_function is not None:
                error_table = validation_function(row2[column_name], j, column_name, credentials, error_table) if validation_function else error_table

#---------- Generate outputs ----------

    software_table = pd.merge(software_table, error_table.groupby(['row'])['type'].apply(list), left_index=True, right_index=True, how="left", sort=False)
    software_table['type'] = software_table['type'].apply(lambda x: "Error" if "Error" in x else "")
    clean = software_table[software_table['type'] != "Error"]
    failed = software_table[software_table['type'] == "Error"]

    error_table = error_table.merge(software_table['identifier'], how="left", left_on="row", right_index=True)
    error_table.insert(1, "identifer", error_table.pop("identifier"))
    error_table.sort_values(by=['row', 'type', 'column'], inplace=True)
    print("\nError Table:")
    print(error_table)
    
    default_style = Styler(font_size=10, vertical_alignment='center', horizontal_alignment='left')
    header_style = Styler(font_size=10, bold=True)

    StyleFrame.A_FACTOR = 1
    StyleFrame.P_FACTOR = 1
    
    errors = StyleFrame(error_table[error_table['type']=="Error"], styler_obj=default_style).apply_headers_style(styler_obj=header_style)
    warnings = StyleFrame(error_table[error_table['type']=="Warning"], styler_obj=default_style).apply_headers_style(styler_obj=header_style)
    info = StyleFrame(error_table[error_table['type']=="Info"], styler_obj=default_style).apply_headers_style(styler_obj=header_style)
    with StyleFrame.ExcelWriter(args.log_file) as writer:
        errors.to_excel(writer, sheet_name="Errors", index=False, best_fit=errors.columns.tolist())
        warnings.to_excel(writer, sheet_name="Warnings", index=False, best_fit=warnings.columns.tolist())
        info.to_excel(writer, sheet_name="Information", index=False, best_fit=info.columns.tolist())

    clean.drop('type', axis=1).to_csv(args.output_file)
    failed.drop('type', axis=1).to_csv(args.failed_file)
    return

 

if __name__ == "__main__":
    main()


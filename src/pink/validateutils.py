"""
Utility functions for validating user input in the spreadsheet.
"""

import sys
from pathlib import Path
import pandas as pd
import json

import requests
import ontopy
import orcid
import datetime
import dateutil.parser 
import pink.parseutils
from rfc3987 import parse
import xlsxwriter


sys.path.append(str(Path(__file__).resolve().parents[1]))

#---------- Basic cleaning functions ----------

def cleanDF(df):
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace("-", "").replace("", pd.NA).fillna(value=pd.NA)
    return(df)

#---------- input/output handling, table setup and management ----------

# Create an empty error table to collect warnings, errors and information on automaticly applied modifications during the parsing and validation of the spreadsheet.
def create_error_table():
    return pd.DataFrame(columns=['row', 'column', 'type', 'message'])

def add_error(error_table, row, column, error_type, message):
    new_error = pd.DataFrame({'row': [row], 'column': [column], 'type': [error_type], 'message': [message]})
    return pd.concat([error_table, new_error], ignore_index=True)

# Read input table with annotations
def read_input_table(args):
    if (args.input_file == ""):
        print(f"\nUsing \n\tinput IRI: {args.input_IRI}\n\tinput sheet: {args.input_sheet}\n\tcorrect entries: {args.output_file}\n\tfailed entries: {args.failed_file}\n\tlog file: {args.log_file}\n")

        googleSW_URL = "https://docs.google.com/spreadsheets/d/"+args.input_IRI+"/export?format=csv&gid="+args.input_sheet
        try:
            annotation_table = pd.read_csv(googleSW_URL)
        except Exception as e:
            print(f"\nError reading Google Sheet: {e}\n")
            return None
    else:
        print(f"\nUsing \n\tinput file: {args.input_file}\n\tinput tab: {args.input_tab}\n\tcorrect entries: {args.output_file}\n\tfailed entries: {args.failed_file}\n\tlog file: {args.log_file}\n")

        try:
            if args.input_tab == "":
                annotation_table = pd.read_excel(args.input_file)
            else:
                annotation_table = pd.read_excel(args.input_file, sheet_name=args.input_tab)
        except Exception as e:
            print(f"\nError reading Excel file: {e}\n")
            return None

    annotation_table = cleanDF(annotation_table)
    print(annotation_table)
    return(annotation_table)

# Read data profile (lines starting with # are ignored)
# Possible datatypes are: 
# - string 
# - IRI
# - URI (resolvable IRI)
# - boolean
# - date
# - SSbDCore (entry exist in SSbD Core ontology)
# - SSbDindividual (individual in the SSbD name space)
# - OrgIRI (ROR or ORCID identifier)
# - PersonIRI (ORCID identifier)
# All these except boolean and date can be lists defined as List[datatype] in the profile table.
def read_profile_table(args):
    try:
        profile_table = pd.read_csv(args.profile_file)
    except Exception as e:
        print(f"\nError reading profile table file: {e}\n")
        return None

    profile_table = profile_table[profile_table['column_name'].str.startswith('#') == False]
    print(f"\nValidation defined by profile table:\n")
    profile_table = cleanDF(profile_table)
    print(profile_table)
    return(profile_table)

# Check if mandatory and recommended columns are present
def check_mandatory_and_recommended_columns(annotation_table, profile_table, error_table):
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        condition = row['condition']

        if column_name not in annotation_table.columns:
            if condition == 'mandatory':
                error_table = add_error(error_table, None, column_name, 'Error', f'Mandatory Column {column_name} is missing from the annotation table.')
            elif condition == 'recommended':
                error_table = add_error(error_table, None, column_name, 'Warning', f'Recommended Column {column_name} is missing from the annotation table.')
            else:
                error_table = add_error(error_table, None, column_name, 'Info', f'Optional Column {column_name} is missing from the annotation table.')
    
    return error_table


# Read ontologies using ontopy
def read_ontology(turtleFile):
    try:
        ontolog = ontopy.get_ontology(turtleFile).load()
    except Exception as e:
            print(f"\nError reading ontology: {e}\n")
            return

    return(ontolog)

 # Read credentials for web services (e.g. ORCID)
def read_credentials(args):
    try:
        credentials = json.load(open(args.credentials_file))
    except Exception as e:
        print(f"\nError reading credentials file: {e}\n")
        return

    print(f"\nUsing credentials from {args.credentials_file}: {credentials}\n")

    if "orcid" in credentials:
        credentials["orcid"]['api'] = orcid.PublicAPI(credentials["orcid"]['client_id'], credentials["orcid"]['client_secret'], sandbox=False) 
        credentials["orcid"]['token'] = credentials["orcid"]['api'].get_search_token_from_orcid()

    return(credentials)

    
def write_error_table(log_file, error_table):
    print(error_table)
    error_table.sort_values(by=['row', 'type', 'column'], inplace=True)
    errors = error_table[error_table['type']=="Error"]
    warnings = error_table[error_table['type']=="Warning"]
    info = error_table[error_table['type']=="Info"]
    with pd.ExcelWriter(log_file, engine="xlsxwriter") as writer:
        errors.to_excel(writer, sheet_name="Errors", index=False)
        warnings.to_excel(writer, sheet_name="Warnings", index=False)
        info.to_excel(writer, sheet_name="Information", index=False)

        workbook = writer.book
        worksheet1 = writer.sheets["Errors"]
        worksheet2 = writer.sheets["Warnings"]
        worksheet3 = writer.sheets["Information"]

        header_format = workbook.add_format(
            {
                "bold": True,
                "text_wrap": False,
                "valign": "middle",
                "align": "center",
            }
        )

        for col_num, value in enumerate(error_table.columns.values):
            worksheet1.write(0, col_num, value, header_format)
            worksheet2.write(0, col_num, value, header_format)
            worksheet3.write(0, col_num, value, header_format)

        worksheet1.autofit()
        worksheet1.freeze_panes(1, 0)
        worksheet2.autofit()
        worksheet2.freeze_panes(1, 0)
        worksheet3.autofit()
        worksheet3.freeze_panes(1, 0)




def write_output_tables(output_file, failed_file, annotation_table, profile_table, error_table):
    errors = error_table[error_table['type']=="Error"]
    failed_rows = errors['row'].unique()
    failed_entries = annotation_table.loc[annotation_table.index.isin(failed_rows)]
    successful_entries = annotation_table.loc[~annotation_table.index.isin(failed_rows)]

    json_file = output_file.replace(".csv", ".json")
    successful_entries.to_json(json_file, orient="records", indent=4)
    
    successful_entries = successful_entries.map(lambda x: ', '.join(str(y) for y in x) if isinstance(x, list) else x)
    successful_entries = successful_entries.map(lambda x: str(x))
    successful_entries = successful_entries.map(lambda x: x.replace('nan', ''))
    successful_entries = successful_entries.map(lambda x: x.replace('NaT', ''))
    successful_entries = successful_entries.map(lambda x: x.replace('<NA>', ''))
    successful_entries = successful_entries[[x for x in profile_table['column_name'].tolist() if x in successful_entries.columns]]
    
    successful_entries.to_csv(output_file, index=False)
    failed_entries.to_csv(failed_file, index=False)


#---------- Transform simplified user input ----------

# Transform columns with list-like values (semicolon-separated) into actual lists
def create_list_columns(annotation_table, profile_table):
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in annotation_table.columns:
            if row['datatype'].startswith('List'):
                annotation_table[column_name] = annotation_table[column_name].apply(
                    lambda x: str(x).replace(',', ';') if (pd.notna(x) and (';' not in str(x))) else x
                )
                annotation_table[column_name] = annotation_table[column_name].apply(
                    lambda x: [item.strip() for item in str(x).split(';')] if pd.notna(x) else x
                )

    return annotation_table

# Transforms yes/no to bool
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

def strings_to_bools(annotation_table, profile_table, error_table):
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in annotation_table.columns:
            if row['datatype'] == 'boolean':
                valid = annotation_table.apply(correct_boolean, column_name=column_name, axis=1, result_type='expand')
                annotation_table[column_name] = valid.pop(column_name)
                valid.dropna(how='all', inplace=True)
                if error_table.empty:
                    error_table = valid
                elif not valid.empty:
                    error_table = pd.concat([error_table, valid])

    return annotation_table, error_table

# Checks and harmonises dates
def translate_string_to_date(row, column_name):
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


def strings_to_dates(annotation_table, profile_table, error_table):
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in annotation_table.columns:
            if row['datatype'] == 'date':
                valid = annotation_table.apply(translate_string_to_date, column_name=column_name, axis=1, result_type='expand')
                annotation_table[column_name] = valid.pop(column_name)
                error_table = pd.concat([error_table, valid.dropna(how='all')])

    return annotation_table, error_table
    

#---------- Translates class/property terms and short IRIs into full IRIs ----------

def retrieve_IRI_from_ontology(column, column_name, ontology, prefixes, error_table, datatype):
    for i, value in column.items():
        if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
           column[i] = value
        elif isinstance(value, list):
            new_value = []
            for v in value:
                new_v = pink.parseutils.check_for_individual_uri(v, ontology, verbose=False)
                if (new_v is not None):
                    if (new_v != v):
                        error_table = add_error(error_table, i, column_name, "Info", f'Term \"{v}\" is in ontology and was resolved to full IRI \"{new_v}\"')
                else:
                    new_v = v
                    if any(iter(map(v.startswith, prefixes)))==True:
                        if ("SSbDCore" in datatype):
                            error_table = add_error(error_table, i, column_name, "Error", f'Term \"{v}\" was not found in ontology.')
                        else:
                            error_table = add_error(error_table, i, column_name, "Warning", f'Term \"{v}\" is considered an individual.')
                    else:
                        if (":" in v):
                            error_table = add_error(error_table, i, column_name, "Warning", f'Prefix of \"{v}\" is not part of ontology.')
                        else:
                            if ("SSbDCore" in datatype):
                                error_table = add_error(error_table, i, column_name, "Error", f'Term \"{v}\" is not in the ontology and not an IRI.')
                            else:
                                new_v = pink.parseutils.add_prefix(v, "ssbd")
                                error_table = add_error(error_table, i, column_name, "Warning", f'Term \"{v}\" is considered an individual and prefix \"ssbd\" was added.')
                new_value.append(new_v)
            column[i] = new_value
        else:
            new_v = pink.parseutils.check_for_individual_uri(value, ontology, verbose=False)
            if (new_v is not None):
                if (new_v != value):
                    error_table = add_error(error_table, i, column_name, "Info", f'Term \"{value}\" is in ontology and was resolved to full IRI \"{new_v}\"')
            else:
                new_v = value
                if any(iter(map(value.startswith, prefixes)))==True:
                    if ("SSbDCore" in datatype):
                        error_table = add_error(error_table, i, column_name, "Error", f'Term \"{value}\" was not found in ontology.')
                    else:
                        error_table = add_error(error_table, i, column_name, "Warning", f'Term \"{value}\" is considered an individual.')
                else:
                    if (":" in value):
                        error_table = add_error(error_table, i, column_name, "Warning", f'Prefix of \"{value}\" is not part of ontology.')
                    else:
                        if ("SSbDCore" in datatype):
                            error_table = add_error(error_table, i, column_name, "Error", f'Term \"{value}\" is not in the ontology and not an IRI.')
                        else:
                            new_v = pink.parseutils.add_prefix(value, "ssbd")
                            error_table = add_error(error_table, i, column_name, "Warning", f'Term \"{value}\" is considered an individual and prefix \"ssbd\" was added.')
            column[i] = new_v

    return(column, error_table)

def replace_short_prefixes(column, column_name, prefixes, error_table):
    for i, value in column.items():
        if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
           column[i] = value
        elif isinstance(value, list):
            new_value = []
            for v in value:
                new_v = pink.parseutils.convert_to_iri(v, prefixes)
                if (new_v is not None):
                    if (new_v != v):
                        error_table = add_error(error_table, i, column_name, "Info", f'Term {v} was resolved to full IRI {new_v}')
                    new_value.append(new_v)
                else:
                    error_table = add_error(error_table, i, column_name, "Error", f'Prefix in {v} is unknown.')
                    new_value.append(v)
            column[i] = new_value
        else:
            new_v = pink.parseutils.convert_to_iri(value, prefixes)
            if (new_v is not None):
                if (new_v != value):
                    error_table = add_error(error_table, i, column_name, "Info", f'Term {value} was resolved to full IRI {new_v}')
                column[i] = new_v
            else:
                error_table = add_error(error_table, i, column_name, "Error", f'Prefix in {value} is unknown.')
                column[i] = value

    return(column, error_table)


#---------- Validate the individual software entries against the profile table ----------
# 
# Check if the person ID is valid by querying the API. If valid, return the name of the person. If not valid, return an error message.
# Currently only ORCIDs are supported as PersonIRI, but this can be extended to other identifiers in the future.
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

# Check if the organisation ID is valid by querying the API. If valid, return the name of the organization. If not valid, return an error message.
# Currently only ROR IDs are supported as OrgIRI, but this can be extended to other identifiers in the future.
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


# Validate correctness of IRIs and URLs, including checking if the latter are resolvable. 

def validate_IRI(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and (item.startswith("https:") or item.startswith("http:")):
                error_table = validate_IRIvalid(item, row, column, credentials, error_table)
            else:
                error_table = add_error(error_table, row, column, 'Error', f'Invalid IRI format in list: {item} - {value}. Expected format: XXXX:XXXXX')

    else:
        if isinstance(value, str) and (value.startswith("https:") or value.startswith("http:")):
            error_table = validate_IRIvalid(value, row, column, credentials, error_table)
        else:
            error_table = add_error(error_table, row, column, 'Error', f'Invalid IRI format or not resolvable: {value}. Expected format: XXXX:XXXXX')
    return error_table

def validate_IRIvalid(value, row, column, credentials, error_table):
    try:
        parse(value, rule='IRI')
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Invalid IRI format: {value}')
        return error_table  # Return IRI is invalid

    error_table = add_error(error_table, row, column, 'Info', f'IRI {value} is valid.')
    return error_table
  

def validate_URLexists(value, row, column, credentials, error_table):
    try:
        parse(value, rule='IRI')
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Invalid IRI format: {value}')
        return error_table  # Return IRI is invalid

    try:
        response = requests.get(value)
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Error accessing IRI {value}: {e}')
        return error_table

    if response.status_code < 400:
        error_table = add_error(error_table, row, column, 'Info', f'URL {value} is valid and accessible: {response.status_code}')
    else:
        error_table = add_error(error_table, row, column, 'Error', f'URL {value} is not accessible: {response.status_code}')

    return error_table


def validate_URL(value, row, column, credentials, error_table):
    if not isinstance(value, list) and (pd.isna(value) or (isinstance(value, float) and np.isnan(value))):
        return error_table
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and (item.startswith("https:") or item.startswith("http:")):
                error_table = validate_URLexists(item, row, column, credentials, error_table)
            else:
                error_table = add_error(error_table, row, column, 'Error', f'Invalid URL format in list: {item} - {value}. Expected format: XXXX:XXXXX')

    else:
        if isinstance(value, str) and (value.startswith("https:") or value.startswith("http:")):
            error_table = validate_URLexists(value, row, column, credentials, error_table)
        else:
            error_table = add_error(error_table, row, column, 'Error', f'Invalid URL format or not resolvable: {value}. Expected format: XXXX:XXXXX')
    return error_table

# Check that entry is boolean or a list of booleans. If not, add an error to the error table.
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

# Check that entry is a date or a list of dates. If not, add an error to the error table.
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


def validate_annotations(annotation_table, profile_table, credentials, error_table):

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
        elif datatype == 'URI' or datatype == 'List[URI]':
            validation_function = validate_URL
        elif "SSbD" in datatype: # to be implemented
            validation_function = validate_IRI
        elif datatype == 'boolean':
            validation_function = validate_boolean
        elif datatype == 'date':
            validation_function = validate_date
        elif datatype == 'string' or datatype == 'List[string]':
            validation_function = None # check for special characters need to be implemented
        else: 
            validation_function = None
        
        print(f"\nValidating column {column_name} of datatype {datatype} with condition {condition} using validation function {validation_function.__name__ if validation_function else 'None'}")
        
        for j, row2 in annotation_table.iterrows():
            if condition == 'mandatory' or condition == 'recommended':
                if not isinstance(row2[column_name], list) and (pd.isna(row2[column_name]) or (isinstance(row2[column_name], float) and np.isnan(row2[column_name]))):
                    type_of_error = 'Error' if condition == 'mandatory' else 'Warning'
                    error_table = add_error(error_table, j, column_name, type_of_error, f'{condition.capitalize()} field {column_name} is missing.')
                    continue
            
            if validation_function is not None:
                error_table = validation_function(row2[column_name], j, column_name, credentials, error_table) if validation_function else error_table

    return error_table

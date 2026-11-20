"""
Utility functions for validating user input in the spreadsheet.
"""

import sys
from pathlib import Path
import pandas as pd
import json
import re

import numpy as np
import requests
import orcid
import datetime
import atexit
import functools
import collections
import dateutil.parser 
import pink.parseutils
from rfc3987 import parse
import xlsxwriter


sys.path.append(str(Path(__file__).resolve().parents[1]))

# Cache web lookups for the current run, so that the same ORCID, ROR ID or URL
# is only requested once (failed requests raise and are not cached).
# A server that does not answer within TIMEOUT seconds raises requests.Timeout.
TIMEOUT = 30

@functools.lru_cache(maxsize=None)
def cached_get(url):
    return requests.get(url, timeout=TIMEOUT)

@functools.lru_cache(maxsize=None)
def cached_orcid_record(api, orcid_id, token):
    return api.read_record_public(orcid_id, 'person', token)

@functools.lru_cache(maxsize=None)
def cached_orcid_anonymous(orcid_id):
    # Anonymous ORCID public API, used when no ORCID credentials are given
    response = requests.get(f"https://pub.orcid.org/v3.0/{orcid_id}/person", headers={"Accept": "application/json"}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()

#---------- Basic cleaning functions ----------

def cleanDF(df):
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.replace("-", "").replace("", pd.NA).fillna(value=pd.NA)
    df = df.rename(columns=lambda x: x.strip())
    return(df)

#---------- input/output handling, table setup and management ----------

# Create an empty error table to collect warnings, errors and information on automaticly applied modifications during the parsing and validation of the spreadsheet.
def create_error_table():
    return pd.DataFrame(columns=['row', 'column', 'type', 'message'])

def add_error(error_table, row, column, error_type, message):
    new_error = pd.DataFrame({'row': [row], 'column': [column], 'type': [error_type], 'message': [message]})
    return pd.concat([error_table, new_error], ignore_index=True)

# Read data profile (lines starting with # are ignored)
# The range of a property is one or more of the following, separated by "|"
# (a value is accepted if it is one of them):
# - a predefined range, written in lower case (see LITERALS and RANGES below):
#   string, boolean, date, dateTime, iri, orcid, ror, ssbd, rights, iana, url
# - an ontology class with a known prefix, e.g. ssbd:Model: the value must be that class,
#   a subclass of it, or an individual of one of them
LITERALS = ("string", "boolean", "date", "dateTime")

def get_ranges(row):
    """Return the alternatives of the range of a profile row, e.g. ["orcid", "ror"]."""
    return [d.strip() for d in str(row['range']).split("|") if d.strip()]

def is_class_range(name):
    """Whether a range alternative is an ontology class (prefix:Name), not a predefined one."""
    return ":" in name

def is_iri_range(row):
    """Whether the values of a profile row are IRIs (all ranges except the literals)."""
    return not any(d in LITERALS for d in get_ranges(row))

def read_profile_table(args, prefixes=None):
    """Read a profile. `prefixes` are the prefixes allowed for classes (default: the PINK prefixes)."""
    if prefixes is None:
        prefixes = pink.parseutils.PREFIXES
    try:
        profile_table = pd.read_csv(args.profile_file)
    except Exception as e:
        print(f"\nError reading profile table file: {e}\n")
        return None

    profile_table = profile_table.rename(columns={"property": "column_name"})  # profiles in profiles/ use "property"
    profile_table = profile_table[profile_table['column_name'].str.startswith('#') == False]
    for _, row in profile_table.iterrows():
        ranges = get_ranges(row)
        for d in ranges:
            if is_class_range(d):
                if d.split(":", 1)[0] not in prefixes:
                    raise ValueError(f"{args.profile_file}: unknown prefix in range {d!r} of {row['column_name']}")
            elif d not in LITERALS and d not in RANGES and d != "iri":
                raise ValueError(f"{args.profile_file}: unknown range {d!r} of {row['column_name']}. "
                                 f"Use one of {', '.join(LITERALS + ('iri',) + tuple(RANGES))} or an ontology class, e.g. ssbd:Model")
        if len(ranges) > 1 and any(d in LITERALS for d in ranges):
            raise ValueError(f"{args.profile_file}: {row['range']!r} of {row['column_name']}: "
                             f"{', '.join(LITERALS)} cannot be combined with other ranges")
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


 # Read credentials for web services (e.g. ORCID)
def read_credentials(args):
    if not Path(args.credentials_file).exists():
        print(f"\nNo credentials file {args.credentials_file} found. ORCIDs are looked up through the anonymous ORCID API.\n")
        return {}
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




#---------- Transform simplified user input ----------

# Transform columns with list-like values (semicolon-separated) into actual lists
def create_list_columns(annotation_table, profile_table):
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in annotation_table.columns:
            if row['range'].startswith('List'):
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
            if row['range'] == 'boolean':
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
            if row['range'] in ('date', 'dateTime'):
                valid = annotation_table.apply(translate_string_to_date, column_name=column_name, axis=1, result_type='expand')
                annotation_table[column_name] = valid.pop(column_name)
                error_table = pd.concat([error_table, valid.dropna(how='all')])

    return annotation_table, error_table
    

#---------- Translates class/property terms and short IRIs into full IRIs ----------

def suggest_term(value, ontology):
    """Return a hint if a term with the same name exists in the ontology (e.g. with another prefix)."""
    name = value.rsplit("/", 1)[-1].rsplit("#", 1)[-1] if value.startswith(("http://", "https://")) else value.split(":", 1)[-1]
    iri = pink.parseutils.check_for_individual_uri(name, ontology, verbose=False)
    if iri is None:
        return ""
    for prefix, namespace in pink.parseutils.PREFIXES.items():
        if iri.startswith(namespace):
            return f" Did you mean {prefix}:{iri[len(namespace):]}?"
    return f" Did you mean {iri}?"

def retrieve_IRI_from_ontology(column, column_name, ontology, prefixes, error_table, strict):
    """Resolve the terms in `column` to IRIs in the ontology.

    If `strict` is true, a term that is not in the ontology is an error, otherwise a warning.
    """
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
                        if strict:
                            error_table = add_error(error_table, i, column_name, "Error", f'Term \"{v}\" was not found in ontology.' + suggest_term(v, ontology))
                        else:
                            error_table = add_error(error_table, i, column_name, "Warning", f'Term \"{v}\" is considered an individual.')
                    else:
                        if (":" in v):
                            if strict:
                                error_table = add_error(error_table, i, column_name, "Error", f'Prefix of \"{v}\" is not part of ontology.' + suggest_term(v, ontology))
                            else:
                                error_table = add_error(error_table, i, column_name, "Warning", f'Prefix of \"{v}\" is not part of ontology.')
                        else:
                            if strict:
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
                    if strict:
                        error_table = add_error(error_table, i, column_name, "Error", f'Term \"{value}\" was not found in ontology.' + suggest_term(value, ontology))
                    else:
                        error_table = add_error(error_table, i, column_name, "Warning", f'Term \"{value}\" is considered an individual.')
                else:
                    if (":" in value):
                        if strict:
                            error_table = add_error(error_table, i, column_name, "Error", f'Prefix of \"{value}\" is not part of ontology.' + suggest_term(value, ontology))
                        else:
                            error_table = add_error(error_table, i, column_name, "Warning", f'Prefix of \"{value}\" is not part of ontology.')
                    else:
                        if strict:
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
# Check if the ORCID is valid by querying the API. If valid, report the name of the person. If not valid, return an error message.
# Used for the range "orcid" (see RANGES).
def validate_orcid(value, row, column, credentials, error_table):
    if (('orcid' not in credentials.keys()) or ('api' not in credentials["orcid"].keys())):
        r = re.compile('https://orcid.org/.{4}-.{4}-.{4}-.{4}')
        if not (len(value) == 37 and r.match(value)):
            error_table = add_error(error_table, row, column, 'Error', f'Invalid ORCID format in list: {value}. Expected format: https://orcid.org/XXXX-XXXX-XXXX-XXXX')
            return error_table

    try:
        orcid_id = value.replace("https://orcid.org/", "")
        if ('orcid' in credentials.keys()) and ('api' in credentials["orcid"].keys()):
            summary = cached_orcid_record(credentials["orcid"]['api'], orcid_id, credentials["orcid"]['token'])
        else:
            summary = cached_orcid_anonymous(orcid_id)
        if summary is None:
            error_table = add_error(error_table, row, column, 'Warning', f'No information for ORCID {value}.')
        else:
           error_table = add_error(error_table, row, column, 'Info', f'ORCID {value} is valid: {summary["name"]['given-names']['value']} {summary["name"]['family-name']['value']}.')
    except Exception as e:
        status = getattr(getattr(e, 'response', None), 'status_code', None)
        if status is not None and status >= 500:  # a server problem, not a problem with the ORCID
            error_table = add_error(error_table, row, column, 'Warning', f'ORCID {value} could not be checked, the ORCID server answered {status}')
        elif isinstance(e, requests.Timeout):
            error_table = add_error(error_table, row, column, 'Warning', f'ORCID {value} could not be checked, the ORCID server did not answer within {TIMEOUT} s')
        else:
            error_table = add_error(error_table, row, column, 'Error', f'Error validating ORCID {value}: {e}')

    return error_table


# Check if the ROR ID is valid by querying the API. If valid, report the name of the organisation. If not valid, return an error message.
# Used for the range "ror" (see RANGES).
def validate_ror(value, row, column, credentials, error_table):
    try:
        query = f"https://api.ror.org/v2/organizations/{value.replace('https://ror.org/', '')}"
        response = cached_get(query)
    except requests.Timeout:
        error_table = add_error(error_table, row, column, 'Warning', f'ROR ID {value} could not be checked, the ROR server did not answer within {TIMEOUT} s')
        return error_table
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Error validating ROR ID {value}: {e}')
        return error_table

    if response.status_code >= 500:  # a server problem, not a problem with the ROR ID
        error_table = add_error(error_table, row, column, 'Warning', f'ROR ID {value} could not be checked, the ROR server answered {response.status_code}')
    elif response.status_code == 200:
        for name in response.json()["names"]:
            if "ror_display" in name["types"]:
                error_table = add_error(error_table, row, column, 'Info', f'ROR ID {value} is valid: {name["value"]}')
                break
    else:
        error_table = add_error(error_table, row, column, 'Error', f'ROR ID {value} is invalid: {response.status_code}')

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

# A media type must be an IANA media type IRI, e.g. iana:application/zip
def validate_MediaTypeIRI(value, row, column, credentials, error_table):
    for item in (value if isinstance(value, list) else [value]):
        if not isinstance(item, str) and pd.isna(item):
            continue
        if isinstance(item, str) and ":" not in item:
            error_table = add_error(error_table, row, column, 'Error', f'Media type "{item}" is not an IRI. Use an IANA media type with prefix, e.g. iana:{item}, or give a free-text format in distribution.format.')
        else:
            error_table = validate_IRI(item, row, column, credentials, error_table)
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
        response = cached_get(value)
    except requests.Timeout:  # the server is slow, which says nothing about the URL
        error_table = add_error(error_table, row, column, 'Warning', f'URL {value} could not be checked, the server did not answer within {TIMEOUT} s')
        return error_table
    except Exception as e:
        error_table = add_error(error_table, row, column, 'Error', f'Error accessing IRI {value}: {e}')
        return error_table

    if response.status_code < 400:
        error_table = add_error(error_table, row, column, 'Info', f'URL {value} is valid and accessible: {response.status_code}')
    elif response.status_code in (401, 403):  # the URL exists, but needs a login or access rights
        error_table = add_error(error_table, row, column, 'Warning', f'URL {value} requires login or access rights: {response.status_code}')
    elif response.status_code >= 500:  # a (possibly temporary) server problem, not a problem with the URL
        error_table = add_error(error_table, row, column, 'Warning', f'URL {value} could not be checked, the server answered {response.status_code}')
    else:
        error_table = add_error(error_table, row, column, 'Error', f'URL {value} is not accessible: {response.status_code}')

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


# Access rights from the EU vocabulary on access rights (prefix "rights")
RIGHTS = "http://publications.europa.eu/resource/authority/access-right/"
ACCESS_RIGHTS = ("CONFIDENTIAL", "NON_PUBLIC", "PUBLIC", "RESTRICTED", "SENSITIVE")

def validate_rights(value, row, column, credentials, error_table):
    if value[len(RIGHTS):] in ACCESS_RIGHTS:
        error_table = add_error(error_table, row, column, 'Info', f'Access rights {value} is valid.')
    else:
        error_table = add_error(error_table, row, column, 'Error', f'Access rights {value} is not one of {", ".join(ACCESS_RIGHTS)}.')
    return error_table


# The predefined ranges for IRIs (besides "iri", any valid IRI).
# For each: whether a value belongs to it, the function that checks it, and the expected format.
Range = collections.namedtuple("Range", "matches check expected")
RANGES = {
    "orcid": Range(lambda v: v.startswith("https://orcid.org/"), validate_orcid,
                   "an ORCID (https://orcid.org/XXXX-XXXX-XXXX-XXXX)"),
    "ror": Range(lambda v: v.startswith("https://ror.org/"), validate_ror,
                 "a ROR ID (https://ror.org/XXXXXXXXX)"),
    "ssbd": Range(lambda v: True, validate_IRI,  # looked up in the ontology in validate_table
                  "a term in the SSbD Core ontology"),
    "rights": Range(lambda v: v.startswith(RIGHTS), validate_rights,
                    f"an access right ({', '.join('rights:' + r for r in ACCESS_RIGHTS)})"),
    "iana": Range(lambda v: True, validate_MediaTypeIRI,
                  "an IANA media type (e.g. iana:application/zip)"),
    "url": Range(lambda v: v.startswith(("http://", "https://")), validate_URLexists,
                 "a resolvable URL (http:// or https://)"),
}


#---------- Ontology classes as range ----------

OWL_CLASS = "http://www.w3.org/2002/07/owl#Class"

def as_list(value):
    """Return the values of a cell as a list (cells may be lists, ;-separated strings or missing)."""
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and v.strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(";") if v.strip()]
    return []


def known_resources(tables, prefixes):
    """Return the resources described in the prepared `tables`, as {IRI: (types, parents)}.

    Used to check properties that refer to resources documented in the same spreadsheet,
    e.g. `hasSoftware` (a software release).
    """
    expand = lambda v: pink.parseutils.convert_to_iri(v, prefixes) or v
    known = {}
    for table in tables:
        columns = {c.removesuffix("[?sep=;]"): c for c in table.columns}
        if "@id" not in columns:
            continue
        for _, row in table.iterrows():
            for iri in as_list(row[columns["@id"]]):
                types = [expand(t) for t in as_list(row[columns["@type"]])] if "@type" in columns else []
                parents = [expand(p) for p in as_list(row[columns["subClassOf"]])] if "subClassOf" in columns else []
                known[expand(iri)] = (types, parents)
    return known


def is_a(iri, class_iri, ontology, known, seen=()):
    """Whether `iri` is the class `class_iri`, a subclass of it, or an individual of one of them.

    Returns None if this cannot be decided: `iri` is neither in the ontology nor in `known`.
    """
    if iri == class_iri:
        return True
    if iri in seen:
        return None
    entity = ontology.search_one(iri=iri) if ontology is not None else None
    if entity is not None:
        cls = ontology.search_one(iri=class_iri)
        if cls is None:
            return False
        if hasattr(entity, "ancestors"):  # a class
            return cls in entity.ancestors()
        return any(cls in c.ancestors() for c in entity.is_a if hasattr(c, "ancestors"))
    if iri in known:
        types, parents = known[iri]
        # A class is checked through its parents, an individual through its types
        candidates = parents if OWL_CLASS in types else types
        answers = [is_a(c, class_iri, ontology, known, seen + (iri,)) for c in candidates]
        if any(answers):
            return True
        return False if any(a is False for a in answers) else None
    return None


def compact(iri, prefixes):
    """Return `iri` with a prefix, e.g. ssbd:Model, if one of `prefixes` fits."""
    matches = [(len(ns), f"{prefix}:{iri[len(ns):]}") for prefix, ns in prefixes.items() if prefix and iri.startswith(ns)]
    return max(matches)[1] if matches else iri


def validate_range(value, row, column, credentials, error_table, ranges, ontology, known, prefixes):
    """Check that each IRI in `value` is of one of the `ranges` (predefined or ontology classes)."""
    classes = [d for d in ranges if is_class_range(d)]
    for item in (value if isinstance(value, list) else [value]):
        if not isinstance(item, str):
            if pd.isna(item):
                continue
            item = str(item)
        # Predefined ranges, e.g. orcid or ror
        for name in ranges:
            if name in RANGES and RANGES[name].matches(item):
                error_table = RANGES[name].check(item, row, column, credentials, error_table)
                break
            if name == "iri":
                error_table = validate_IRI(item, row, column, credentials, error_table)
                break
        else:
            # Ontology classes: the value must be the class, a subclass or an individual of it
            answers = [is_a(item, pink.parseutils.convert_to_iri(c, prefixes) or c, ontology, known) for c in classes]
            hint = suggest_term(item, ontology) if ontology is not None else ""
            if any(answers):
                error_table = validate_IRIvalid(item, row, column, credentials, error_table)
            elif classes and all(a is False for a in answers):
                error_table = add_error(error_table, row, column, 'Error',
                                        f'{compact(item, prefixes)} is not a {" or ".join(classes)}.')
            elif classes:
                error_table = add_error(error_table, row, column, 'Error',
                                        f'{compact(item, prefixes)} was not found in the ontology or in the spreadsheet '
                                        f'(it must be a {" or ".join(classes)}).' + hint)
            else:
                expected = " or ".join(RANGES[name].expected for name in ranges if name in RANGES)
                error_table = add_error(error_table, row, column, 'Error',
                                        f'{item} is not in the range of {column} ({" | ".join(ranges)}). Expected {expected}.')
    return error_table


def validate_annotations(annotation_table, profile_table, credentials, error_table, ontology=None, known=None, prefixes=None):

    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        range_ = row['range']
        condition = row['condition']
        if column_name not in annotation_table.columns:
            continue  # missing columns are reported by check_mandatory_and_recommended_columns

        if is_iri_range(row):
            validation_function = functools.partial(validate_range, ranges=get_ranges(row), ontology=ontology,
                                                    known=known or {}, prefixes=prefixes or pink.parseutils.PREFIXES)
            validation_function.__name__ = f"validate_range({range_})"
        elif range_ == 'boolean':
            validation_function = validate_boolean
        elif range_ in ('date', 'dateTime'):
            validation_function = validate_date
        else:  # string: check for special characters need to be implemented
            validation_function = None

        print(f"\nValidating column {column_name} with range {range_} with condition {condition} using validation function {validation_function.__name__ if validation_function else 'None'}")
        
        for j, row2 in annotation_table.iterrows():
            if condition == 'mandatory' or condition == 'recommended':
                if not isinstance(row2[column_name], list) and (pd.isna(row2[column_name]) or (isinstance(row2[column_name], float) and np.isnan(row2[column_name]))):
                    type_of_error = 'Error' if condition == 'mandatory' else 'Warning'
                    error_table = add_error(error_table, j, column_name, type_of_error, f'{condition.capitalize()} field {column_name} is missing.')
                    continue
            
            if validation_function is not None:
                error_table = validation_function(row2[column_name], j, column_name, credentials, error_table)

    return error_table


# A computation must be a subclass of at least one SSbD assessment (SSbD Assessment level 1, 2 or 3)
def check_assessment(table, ontology, error_table):
    assessment = ontology.search_one(iri="https://w3id.org/ssbd/Assessment")
    column = "subClassOf[?sep=;]" if "subClassOf[?sep=;]" in table.columns else "subClassOf"
    for row, value in table[column].items():
        parents = value.split(";") if isinstance(value, str) else (value if isinstance(value, list) else [])
        classes = [ontology.search_one(iri=iri.strip()) for iri in parents]
        if not any(c is not None and assessment in c.ancestors() for c in classes):
            error_table = add_error(error_table, row, "subClassOf", "Error", "No SSbD assessment given: at least one of the SSbD Assessment levels must be filled in.")
    return error_table


def ontology_namespaces(ontology, prefixes):
    """Return the namespaces of the terms in `ontology`, and the prefixes (with ":") for them.

    SSbD Core includes terms from other ontologies with their own IRIs (EMMO, CHEMINF, ChEBI, ...).
    Used to tell a term that is missing from the ontology from a term with a prefix
    that is not part of the ontology.
    """
    namespaces = set()
    for entity in list(ontology.classes()) + list(ontology.properties()) + list(ontology.individuals()):
        iri = entity.iri
        namespaces.add(iri[:max(iri.rfind("#"), iri.rfind("/")) + 1])
    namespaces.discard("")
    known = [f"{prefix}:" for prefix, namespace in prefixes.items() if prefix and namespace in namespaces]
    return known + sorted(namespaces)


def resolve_labels(column, column_name, ontology, error_table):
    """Replace terms given by their label (no prefix, not an IRI) with their IRI in the ontology."""
    for i, value in column.items():
        values = value if isinstance(value, list) else [value]
        new_values = []
        for v in values:
            if isinstance(v, str) and ":" not in v:
                iri = pink.parseutils.check_for_individual_uri(v, ontology, verbose=False)
                if iri is not None and iri != v:
                    error_table = add_error(error_table, i, column_name, "Info", f'Term "{v}" is in ontology and was resolved to full IRI "{iri}"')
                    v = iri
            new_values.append(v)
        column[i] = new_values if isinstance(value, list) else new_values[0]
    return column, error_table


def validate_table(table, profile_table, ontology, credentials, prefixes=None, known=None):
    """Validate a table against a profile table and return the error table.

    The columns of `table` are property names (as in the prepared tables).
    The table itself is not changed.
    `prefixes` maps known prefixes to IRIs (default: the PINK prefixes).
    `known` are the resources documented in the same spreadsheet (see `known_resources`),
    used for ranges that are ontology classes.
    """
    if prefixes is None:
        prefixes = pink.parseutils.PREFIXES
    table = table.copy()
    table = table.mask(table == "")  # empty cells in the prepared tables are missing values
    error_table = create_error_table()

    # Prepared tables mark list columns with [?sep=;]: split them into lists
    for col in [c for c in table.columns if c.endswith("[?sep=;]")]:
        table[col] = table[col].apply(lambda x: [v.strip() for v in str(x).split(";")] if pd.notna(x) else x)
    table.columns = [c.removesuffix("[?sep=;]") for c in table.columns]

    # Missing mandatory columns are reported as errors, and the validation continues.
    error_table = check_mandatory_and_recommended_columns(table, profile_table, error_table)

    # Validate and modify simplified user input
    # Simplifications include
    # - semicolon-separated lists
    # - Yes/No for boolean columns
    # - date columns in various formats
    # - no prefix in columns SSbD Assessment levels and, accessRights
    table = create_list_columns(table, profile_table)
    table, error_table = strings_to_bools(table, profile_table, error_table)
    table, error_table = strings_to_dates(table, profile_table, error_table)

    # Add prefix to specific columns and remove extra content
    if "accessRights" in table.columns:
        table["accessRights"] = table["accessRights"].apply(pink.parseutils.add_prefix, prefix="rights")

    if "inTierLevel" in table.columns:
        table["inTierLevel"] = table["inTierLevel"].apply(pink.parseutils.remove_extra_text)

    # Check ontology - the SSbD Core ontology, including the terms it takes from other
    # ontologies with their own IRIs (EMMO, CHEMINF, ChEBI, ...)
    in_ontology = ontology_namespaces(ontology, prefixes) if ontology is not None else []
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        ranges = get_ranges(row)
        if column_name not in table.columns or ontology is None:
            continue
        if "ssbd" in ranges:
            # Only SSbD Core terms are accepted if that is the only range
            table[column_name], error_table = retrieve_IRI_from_ontology(table[column_name].copy(deep=True), column_name, ontology, in_ontology, error_table, strict=(ranges == ["ssbd"]))
        elif any(is_class_range(d) for d in ranges):
            table[column_name], error_table = resolve_labels(table[column_name].copy(deep=True), column_name, ontology, error_table)

    # IRI columns may refer to terms outside the ontology. But a prefixed term that is not
    # in the ontology, while the same name is (e.g. datasettype:Dataset for ssbd:Dataset),
    # probably has a wrong prefix: warn about it.
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in table.columns and get_ranges(row) == ['iri'] and ontology is not None:
            for j, value in table[column_name].items():
                for v in (value if isinstance(value, list) else [value]):
                    if (isinstance(v, str) and ":" in v and not v.startswith(("http://", "https://"))
                            and pink.parseutils.check_for_individual_uri(v, ontology) is None):
                        hint = suggest_term(v, ontology)
                        if hint:
                            error_table = add_error(error_table, j, column_name, "Warning", f'Term "{v}" is not in the ontology.' + hint)

    # Replace known prefixes
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in table.columns and is_iri_range(row):
            table[column_name], error_table = replace_short_prefixes(table[column_name].copy(deep=True), column_name, prefixes, error_table)

    # Validate the individual entries against the profile table
    error_table = validate_annotations(table, profile_table, credentials, error_table, ontology, known, prefixes)
    return error_table


#---------- Datamodels (the datum columns of the dataset type tab) ----------

def save_namespace_caches_at_exit():
    """Save the IRI caches of tripper namespaces while Python can still do it.

    The unit lookup of dlite fills the cache of tripper's EMMO namespace. tripper saves it
    in Namespace.__del__, which runs when Python shuts down and prints an ImportError
    traceback (a bug in tripper). So the caches are saved at exit instead, and emptied so
    that __del__ has nothing left to save.
    """
    import gc
    from tripper import Namespace

    def save():
        for ns in gc.get_objects():
            if isinstance(ns, Namespace) and ns._iris:
                ns._save_cache()
                ns._iris = {}

    if not getattr(save_namespace_caches_at_exit, "registered", False):
        atexit.register(save)
        save_namespace_caches_at_exit.registered = True


# A datum name is used in the IRI of the datum (<datamodel IRI>#<name>)
DATUM_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def datum_brackets(columns):
    """Return the brackets of the datums in `columns`, e.g. ["[1]", "[2]"] for datumName[1], datumName[2]."""
    return [m.group(1) or "" for c in columns if (m := re.fullmatch(r"datumName(\[[^\]]*\])?", str(c)))]


def validate_datamodels(datamodels, prefixes):
    """Validate the datamodel table made by pink.prepare.prepare_datamodels and return the error table.

    The datamodels are read by dlite (DMTable), which checks the type of each datum.
    Here is only checked what dlite does not check (or where it fails without a clear message):
    that each datum has a name that can be used in an IRI and is unique, that a datamodel has datums,
    that the units are known (they are looked up in EMMO by dlite) and that mappings are IRIs.
    """
    import warnings
    import dlite
    from dlite.dataset import MissingUnitError, get_unit_iri
    save_namespace_caches_at_exit()
    from dlite.table import DMTable

    error_table = create_error_table()
    text = lambda v: "" if (not isinstance(v, str) and pd.isna(v)) else str(v).strip()
    brackets = datum_brackets(datamodels.columns)
    fields = [c.removesuffix(brackets[0]) for c in datamodels.columns if brackets and c.startswith("datum") and c.endswith(brackets[0])]

    for row, dm in datamodels.iterrows():
        uri = text(dm["@id"])
        if not uri.startswith(("http://", "https://")):
            error_table = add_error(error_table, row, "@id", "Error", f"The identifier {uri} of the datamodel has no known prefix.")
        names = {}
        named = []  # brackets of the datums with a name, in the order dlite reads them
        for b in brackets:
            get = lambda field: text(dm.get(field + b))
            name = get("datumName")
            if not name:
                if any(get(f) for f in fields):
                    error_table = add_error(error_table, row, "datumName" + b, "Error", f"Datum {b} has no name.")
                continue
            if not DATUM_NAME.fullmatch(name):
                error_table = add_error(error_table, row, "datumName" + b, "Error",
                                        f'Datum name "{name}" may only contain letters, digits and _, and not start with a digit '
                                        "(it is used in the IRI of the datum).")
            elif name in names:
                error_table = add_error(error_table, row, "datumName" + b, "Error", f'Datum name "{name}" is used more than once in the datamodel.')
            names.setdefault(name, b)
            named.append(b)
            unit = get("datumUnit")
            if unit:
                try:
                    get_unit_iri(unit)
                except MissingUnitError:
                    error_table = add_error(error_table, row, "datumUnit" + b, "Warning",
                                            f'Unit "{unit}" was not found in EMMO: it is left out of the datamodel.')
            mapping = get("datumMapping")
            if mapping:
                iri = pink.parseutils.convert_to_iri(mapping, prefixes)
                if not iri.startswith(("http://", "https://")):
                    error_table = add_error(error_table, row, "datumMapping" + b, "Error",
                                            f'Mapping "{mapping}" is not an IRI with a known prefix.')
                else:
                    error_table = validate_IRIvalid(iri, row, "datumMapping" + b, None, error_table)
        if not names:
            error_table = add_error(error_table, row, "datumName" + (brackets[0] if brackets else ""), "Error", "The datamodel has no datum with a name.")
            continue
        if not uri.startswith(("http://", "https://")):
            continue

        # Let dlite read each datum, as generate-graph does, and report what it does not accept (e.g. an unknown type)
        table = [list(datamodels.columns), [text(v) for v in dm.values]]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            props = DMTable(table, unit_handling="force").dmdicts[uri].get("properties", [])
        for prop, b in zip(props, named):
            dims = {dim: "" for dim in prop.get("shape", [])}
            try:
                with dlite.silent:
                    dlite.Metadata.from_dict({"uri": f"{uri}/validate/{row}/{prop['name']}", "description": "",
                                              "dimensions": dims, "properties": [prop]})
            except Exception as e:
                message = re.split(r"""["'\n]""", str(e))[0].strip().rstrip(":")
                error_table = add_error(error_table, row, "datumType" + b, "Error",
                                        f'dlite does not accept datum "{prop["name"]}": {message}')
    return error_table

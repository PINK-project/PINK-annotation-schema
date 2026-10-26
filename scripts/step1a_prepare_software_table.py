"""
Script parses a user provided spreadsheet with annotations for software documentation.

It accepts Excel files or Goole spreadsheets and validates data before it is saved to a csv file. 
Validation errors and warnings are saved to a log file. The csv files are then used in the next step to create
triples and save them to the triplestore. 

Validation is based on a profile table that defines the expected columns (lines starting with # are ignored), their datatypes and 
whether they are mandatory, recommended or optional.

Possible datatypes are: 
- string 
- IRI
- URL (resolvable IRI)
- boolean
- date
- SSbDCore (entry exist in SSbD Core ontology)
- SSbDindividual (individual in the SSbD name space)
- OrgIRI (ROR or ORCID identifier)
- PersonIRI (ORCID identifier)

All these except boolean and date can be lists defined as List[datatype] in the profile table.

"""

import sys
from pathlib import Path
import argparse
import pandas as pd
import json

from pink.parseutils import PREFIXES as prefixes
import pink.validateutils

import ontopy

#import openpyxl
#from styleframe import StyleFrame, Styler
#import numpy as np

#import re
#
#import orcid
#import requests
#import datetime
#import dateutil.parser 
#from rfc3987 import parse

sys.path.append(str(Path(__file__).resolve().parents[1]))


#----------------------------------------- Main ----------------------------------

def main():

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
    parser.add_argument("-p", help="Name of the file with the profile table", dest="profile_file", default="input/dataprofile.csv")
    parser.add_argument("-c", help="Name of the file with web service credentials", dest="credentials_file", default="credentials.json")
    args = parser.parse_args()

    print(f"\n --- Software annotation validation script {sys.argv[0]} ---")

    error_table = pink.validateutils.create_error_table()

#---------- Read Excel or Google Sheet with software annotations ----------

    software_table = pink.validateutils.read_input_table(args)
    if (software_table is None):
        return

#    software_table = software_table.head(2)  # Limit to first X rows for testing purposes, remove this line for full processing

    profile_table = pink.validateutils.read_profile_table(args)
    if (profile_table is None):
        return

    ssbd = pink.validateutils.read_ontology("https://ssbd-ontology.github.io/core/core-inferred.ttl")
    if (ssbd is None):
        return

    credentials = pink.validateutils.read_credentials(args)
    if (credentials is None):
        return
    
#---------- Validate the columns in the software table against the profile table ----------

# Script exits if mandatory columns are not present and provides the error messages in the error file.

    error_table = pink.validateutils.check_mandatory_and_recommended_columns(software_table, profile_table, error_table)
    if (not error_table[error_table['type'] == 'Error'].empty):
        print("\nErrors found in the annotation table. Please check the log file for details.")
        pink.validateutils.write_error_table(args.log_file, error_table)
        return

#---------- Validate and modify simplified user input ----------

# Simplifications include
# - semicolon-separated lists
# - Yes/No for boolean columns 
# - date columns in various formats
# - no prefix in columns SSbD Assessment levels and, accessRights

    software_table = pink.validateutils.create_list_columns(software_table, profile_table)
    software_table, error_table = pink.validateutils.strings_to_bools(software_table, profile_table, error_table)
    software_table, error_table = pink.validateutils.strings_to_dates(software_table, profile_table, error_table)

    # Add prefix to specific columns and remove extra content 
    if "accessRights" in software_table.columns:
        software_table["accessRights"] = software_table["accessRights"].apply(pink.parseutils.add_prefix, prefix="rights")

    if "inTierLevel" in software_table.columns:
        software_table["inTierLevel"] = software_table["inTierLevel"].apply(pink.parseutils.remove_extra_text)

    # Check ontology - currently only SSbD including the relevant EMMO parts
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        datatype = row['datatype']
        if (column_name in software_table.columns) and ("SSbD" in row['datatype']):
            software_table[column_name], error_table = pink.validateutils.retrieve_IRI_from_ontology(software_table[column_name].copy(deep=True), column_name, ssbd, ["ssbd:", "emmo:", "https://w3id.org/ssbd/", "https://w3id.org/emmo/"], error_table, datatype)

    # Replace known prefixes
    for i, row in profile_table.iterrows():
        column_name = row['column_name']
        if column_name in software_table.columns and ("IRI" in row['datatype'] or "URL" in row['datatype'] or "SSbD" in row['datatype']):
            software_table[column_name], error_table = pink.validateutils.replace_short_prefixes(software_table[column_name].copy(deep=True), column_name, prefixes, error_table)

#---------- Validate the individual software entries against the profile table ----------
    error_table = pink.validateutils.validate_annotations(software_table, profile_table, credentials, error_table)

    error_table = error_table.merge(software_table['identifier'], how="left", left_on="row", right_index=True)
    error_table.insert(1, "identifer", error_table.pop("identifier"))
    pink.validateutils.write_error_table(args.log_file, error_table)
    pink.validateutils.write_output_tables(args.output_file, args.failed_file, software_table, profile_table, error_table)

if __name__ == "__main__":
    main()


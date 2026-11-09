#!/bin/bash
python scripts/step1a_prepare_software_table.py -I 1ENcdSmaOwC3xFlOLnVgUrWP4dnTvezzWZzYxM9jMzDs -o KI_sw_clean.csv -O KI_comp_clean.csv -e KI_sw_failed.csv -l KI_sw_log.xlsx -t software
python scripts/step1a_prepare_software_table.py -I 1BLUnSdW66lNdrBKJTpILzHFgsAdgeEO2GqohP82oTvs -o LIST_sw_clean.csv -O LIST_comp_clean.csv -e LIST_sw_failed.csv -l LIST_sw_log.xlsx -t software
python scripts/step1a_prepare_software_table.py -I 18UqWYfq6AQMv7ZV-pcZJWc9yAr6VBoXarhxatwBxIWA -o NTUA_sw_clean.csv -O NTUA_comp_clean.csv -e NTUA_sw_failed.csv -l NTUA_sw_log.xlsx -t software

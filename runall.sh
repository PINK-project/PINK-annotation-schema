#!/bin/bash
python.exe scripts/step1a_prepare_software_table.py -I 1ENcdSmaOwC3xFlOLnVgUrWP4dnTvezzWZzYxM9jMzDs -o output/KI_sw_clean.csv -O output/KI_comp_clean.csv -e output/KI_sw_failed.csv -l output/KI_sw_log.xlsx -t software
python.exe scripts/step1a_prepare_software_table.py -I 1BLUnSdW66lNdrBKJTpILzHFgsAdgeEO2GqohP82oTvs -o output/LIST_sw_clean.csv -O output/LIST_comp_clean.csv -e output/LIST_sw_failed.csv -l output/LIST_sw_log.xlsx -t software
python.exe scripts/step1a_prepare_software_table.py -I 18UqWYfq6AQMv7ZV-pcZJWc9yAr6VBoXarhxatwBxIWA -o output/NTUA_sw_clean.csv -O output/NTUA_comp_clean.csv -e output/NTUA_sw_failed.csv -l output/NTUA_sw_log.xlsx -t software

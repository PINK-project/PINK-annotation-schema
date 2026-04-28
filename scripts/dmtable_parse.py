from dlite.table import DMTable
from dlite import get_instance
from tripper import Triplestore
from dlite.dataset import add_dataset

# create triplestore as helper for 
# making datamodels into rdf
ts = Triplestore('rdflib')

# Parse the csv table
dmtable = DMTable.from_csv("datamodels.csv")

# Create the datamodels
dmtable.get_datamodels()

# get

add_dataset(ts, get_instance('http://pink-project.eu/omics/transcriptPTGS-BMDoutput'))

dmtable.to_triplestore(ts)

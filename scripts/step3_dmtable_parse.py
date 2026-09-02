from dlite.table import DMTable
from dlite import get_instance
from tripper import Triplestore
from dlite.dataset import add_dataset

# create triplestore as helper for 
# making datamodels into rdf
ts = Triplestore('rdflib')

# Parse the csv table
print('parsing csv')
dmtable = DMTable.from_csv("datamodels.csv", unit_handling="ignore")
print('finished parsing csv')

# Create the datamodels
print('creating datamodels')
dmtable.get_datamodels()
print('finished creating datamodels')

dmtable.to_triplestore(ts)

print('finished putting into ts')

print('serializing to turtle')
ts.serialize('datamodels.ttl', format='turtle')
print('finished seralizing to turtle')

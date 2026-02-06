from pyshacl import validate

from tripper import Triplestore, Literal
from tripper.datadoc import save_datadoc, search_iris, load_dict, delete, search, get_keywords
from tripper.datadoc.tabledoc import TableDoc
from pandas import read_csv


#keywords = get_keywords('keywords.yaml')
kw = get_keywords()

kw.add_prefix('emmo','https://w3id.org/emmo/hume#', replace=True) 


kw.load_yaml('https://pink-project.github.io/PINK-annotation-schema/context/keywords.yaml', redefine='allow')



ts = Triplestore('rdflib')

infile = 'sw.csv'

sw = read_csv('sw.csv')

activity_columns = ['title', 'inputDatasetType', 'outputDatasetType']

comp = sw[activity_columns]

comp.rename(columns={"inputDatasetType": "hasInput", "outputDatasetType": "hasOutput"}, inplace=True)

sw = sw.drop(columns=["inputDatasetType", "outputDatasetType"])

# We have to decide how to handle Indicator, it is currently a class.
# SsbdDimensions are waiting for UoB
# SsbdDescription waiting for UoB
# hasGUI has just disappeared, to be readded

sw = sw.drop(columns=["indicator", "SsbdDescription", "hasGUI", "chemicalClass"])
#sw.rename(columns={"indicator": "Indicator"}, inplace=True)  


sw.rename(columns={"modelType": "implementsModel", "SsbdDimension": "ssbdDimension", "identifier": "@id"}, inplace=True)

sw.to_csv('sw_clean.csv', index=False)

datadocumentation = TableDoc.parse_csv(
        'sw_clean.csv',
        keywords=kw,
        )

#datadocumentation = TableDoc.fromdicts(
#        sw.to_dict(), 
#        #prefixes={},
#        keywords=kw,
#)


datadocumentation.save(ts)

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

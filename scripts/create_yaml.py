from tripper import Triplestore
from tripper.datadoc import get_keywords

ts =  Triplestore('rdflib')

ts.parse('../pink_annotation_schema.ttl')

kw = get_keywords()

kw.add_prefix('pink', 'https://w3id.org/pink#')

kw.load_rdf(ts, redefine='allow')

kw.save_yaml('generated_kw.yml')

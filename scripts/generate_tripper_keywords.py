from tripper import Triplestore
from tripper.datadoc import get_keywords
import logging

# Note that logging to screen is not always happening
logging.getLogger().setLevel(logging.INFO)

ts =  Triplestore('rdflib')

ts.parse('../pink_annotation_schema.ttl')

kw = get_keywords()

kw.add_prefix('pink', 'https://w3id.org/pink#')

kw.load_rdf(ts, redefine='allow')

kw.save_yaml('../context/generated_keywords.yml')

kw.save_context('../context/pink_context.json')


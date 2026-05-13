from tripper import Triplestore
from tripper.datadoc import search
import keyring


# Connect to PINK KB

#username = keyring.get_password("PINK_graphdb", "username")
#password = keyring.get_password("PINK_graphdb", "password")

#kb = Triplestore(
#        backend="sparqlwrapper", 
#        base_iri="https://graphdb.pink-project.eu/repositories/testing", 
#        username=username, 
#        password=password, 
#        update_iri="https://graphdb.pink-project.eu/repositories/testing/statements",
#        )


kb = Triplestore('rdflib')

kb.parse('https://w3id.org/ssbd/')  # Ontology
kb.parse('https://w3id.org/emmo/1.0.3')
kb.parse('pink-agents.ttl') # agents
kb.parse('googlespreadsheet_resources.ttl') # All the resources
kb.parse('datamodels.ttl') # datamodels



query1 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX cheminf: <http://semanticscience.org/resource/>

SELECT DISTINCT ?subclass ?label
WHERE {
  ?subclass rdfs:subClassOf+ cheminf:CHEMINF_000018 .
  OPTIONAL { ?subclass rdfs:label ?label }
}
ORDER BY ?label
"""

results1 = kb.query(query1)

query2 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX cheminf: <http://semanticscience.org/resource/>

SELECT DISTINCT ?subclass ?label
WHERE {
  ?subclass rdfs:subClassOf+ cheminf:CHEMINF_000085 .
  OPTIONAL { ?subclass rdfs:label ?label }
}
ORDER BY ?label
"""

results2 = kb.query(query2)


query3 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX emmo: <https://w3id.org/emmo#>
PREFIX datasettype: <https://pink-project.eu/datasettype/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX ssbd: <https://w3id.org/ssbd/>

SELECT DISTINCT ?datasetType ?label ?prefLabel ?description ?cardinality ?restrictionType
WHERE {
  ?datasetType rdfs:subClassOf+ ssbd:Dataset .

  ?datasetType rdfs:subClassOf ?restriction .

  ?restriction a owl:Restriction ;
               owl:onProperty emmo:EMMO_b19aacfc_5f73_4c33_9456_469c1e89a53e .

  {
    # Pattern 1: qualified restriction
    ?restriction owl:onClass <https://pink-project.eu/datasettype/SMILES#SMILES> .
    OPTIONAL { ?restriction owl:qualifiedCardinality ?cardinality . }
    BIND(owl:onClass AS ?restrictionType)
  }
  UNION
  {
    # Pattern 2: standard OWL restrictions
    ?restriction ?restrictionType <https://pink-project.eu/datasettype/SMILES#SMILES> .
    VALUES ?restrictionType {
      owl:someValuesFrom
      owl:allValuesFrom
      owl:hasValue
    }
  }

  OPTIONAL { ?datasetType rdfs:label ?label . }
  OPTIONAL { ?datasetType skos:prefLabel ?prefLabel . }
  OPTIONAL { ?datasetType dcterms:description ?description . }
}
ORDER BY ?prefLabel ?label ?datasetType
"""

results3 = kb.query(query3)




query4 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX datasettype: <https://pink-project.eu/datasettype/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX ssbd: <https://w3id.org/ssbd/>

SELECT DISTINCT
  ?assessment
  (COALESCE(?prefLabel, ?label, ?title, STR(?assessment)) AS ?name)
  (COALESCE(?description, "") AS ?descriptionText)
  ?restrictionType
WHERE {
  ?assessment rdfs:subClassOf+ ssbd:Assessment .

  ?assessment rdfs:subClassOf ?restriction .

  ?restriction a owl:Restriction ;
               owl:onProperty ssbd:hasInput .

  {
    ?restriction owl:onClass datasettype:SMILES .
    BIND(owl:onClass AS ?restrictionType)
  }
  UNION
  {
    ?restriction ?restrictionType datasettype:SMILES .
    VALUES ?restrictionType {
      owl:someValuesFrom
      owl:allValuesFrom
      owl:hasValue
    }
  }

  OPTIONAL { ?assessment rdfs:label ?label . }
  OPTIONAL { ?assessment skos:prefLabel ?prefLabel . }
  OPTIONAL { ?assessment dcterms:title ?title . }
  OPTIONAL { ?assessment dcterms:description ?description . }
}
ORDER BY ?name ?assessment
"""

results4 = kb.query(query4)


activity_uri = "https://w3id.org/pink/activity/activity0"

query5 = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX ssbd: <https://w3id.org/ssbd/>
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT
  ?activity
  ?software
  (COALESCE(?softwarePrefLabel, ?softwareLabel, ?softwareTitle, STR(?software)) AS ?softwareName)
WHERE {{
  BIND(<{activity_uri}> AS ?activity)

  ?activity rdfs:subClassOf ?restriction .

  ?restriction a owl:Restriction ;
               owl:onProperty ssbd:hasSoftware ;
               owl:hasValue ?software .

  OPTIONAL {{ ?software skos:prefLabel ?softwarePrefLabel . }}
  OPTIONAL {{ ?software rdfs:label ?softwareLabel . }}
  OPTIONAL {{ ?software dcterms:title ?softwareTitle . }}
}}
ORDER BY ?softwareName
"""

results5 = kb.query(query5)




target_property = "http://www.semanticweb.org/ontologies/cheminf.owl#CHEMINF_000085"


target_property = "http://semanticscience.org/resource/CHEMINF_000085"

query_all = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX emmo: <https://w3id.org/emmo#>
PREFIX datasettype: <https://pink-project.eu/datasettype/>
PREFIX cheminf: <http://semanticscience.org/resource/>
PREFIX ssbd: <https://w3id.org/ssbd/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT DISTINCT ?software

WHERE {{
  # 1. Find subclasses of the requested CHEMINF property
  ?propertyClass rdfs:subClassOf+ <{target_property}> .

  # 2. Find dataset types that have this property class as datum
  # Are not considering datamoedels with uri neq to datasettype
  ?datasetType rdfs:subClassOf+ ssbd:Dataset ;
               rdfs:subClassOf ?datasetRestriction .

  ?datasetRestriction a owl:Restriction ;
                      owl:onProperty emmo:EMMO_b19aacfc_5f73_4c33_9456_469c1e89a53e .

  {{
    ?datasetRestriction owl:onClass ?propertyClass .
  }}
  UNION
  {{
    ?datasetRestriction ?datasetRestrictionType ?propertyClass .
    VALUES ?datasetRestrictionType {{
      owl:someValuesFrom
      owl:allValuesFrom
      owl:hasValue
    }}
  }}

  # 3. Find assessments/activities that have this dataset type as input
  ?assessment rdfs:subClassOf+ ssbd:Assessment ;
              rdfs:subClassOf ?inputRestriction .

  ?inputRestriction a owl:Restriction ;
                    owl:onProperty ssbd:hasInput .

  {{
    ?inputRestriction owl:onClass ?datasetType .
  }}
  UNION
  {{
    ?inputRestriction ?inputRestrictionType ?datasetType .
    VALUES ?inputRestrictionType {{
      owl:someValuesFrom
      owl:allValuesFrom
      owl:hasValue
    }}
  }}

  # 4. Find software used by those assessments/activities
  ?assessment rdfs:subClassOf ?softwareRestriction .

  ?softwareRestriction a owl:Restriction ;
                       owl:onProperty ssbd:hasSoftware ;
                       owl:hasValue ?software .

  OPTIONAL {{ ?propertyClass rdfs:label ?propertyLabel . }}

  OPTIONAL {{ ?datasetType rdfs:label ?datasetLabel . }}
  OPTIONAL {{ ?datasetType skos:prefLabel ?datasetPrefLabel . }}

  OPTIONAL {{ ?assessment rdfs:label ?assessmentLabel . }}
  OPTIONAL {{ ?assessment skos:prefLabel ?assessmentPrefLabel . }}
  OPTIONAL {{ ?assessment dcterms:title ?assessmentTitle . }}

  OPTIONAL {{ ?software rdfs:label ?softwareLabel . }}
  OPTIONAL {{ ?software skos:prefLabel ?softwarePrefLabel . }}
  OPTIONAL {{ ?software dcterms:title ?softwareTitle . }}
}}
ORDER BY ?softwareName ?assessmentName ?datasetName ?propertyName
"""

results_all = kb.query(query_all)

for row in results_all:
    print(row)





kb.serialize('everything.ttl', format='turtle')
























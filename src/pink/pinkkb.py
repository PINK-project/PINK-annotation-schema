"""
Utility for getting classes defined in PINKKB.
Note that for this to work out ofthe box 
the tripper config-file must be configured:
```~/.config/tripper/session.yaml
PINKKB:
  backend: sparqlwrapper
  base_iri: https://graphdb.pink-project.eu/repositories/pinkish
  update_iri: https://graphdb.pink-project.eu/repositories/pinkish/statements
  username: you pink kb username
  password: KEYRING
```
You can also add the password in plantext, but that is not preferred.
"""

from tripper import Session, OWL
import unicodedata, hashlib, re

def pinkkb_classes():
    """
    Returns a context with all the classes in the PINK KB.
    This can then be merged with other cotexts at will.
    """

    session=Session()

    pinkkb=session.get_triplestore("PINKKB")

    query = """
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?class (COALESCE(?prefLabel, ?rdfsLabel) AS ?label)
WHERE {
    VALUES ?classType { owl:Class rdfs:Class }
    ?class rdf:type ?classType .

    OPTIONAL {
        ?class skos:prefLabel ?prefLabel .
        FILTER(LANG(?prefLabel) = "" || LANGMATCHES(LANG(?prefLabel), "en"))
    }

    OPTIONAL {
        ?class rdfs:label ?rdfsLabel .
        FILTER(LANG(?rdfsLabel) = "" || LANGMATCHES(LANG(?rdfsLabel), "en"))
    }

    FILTER(BOUND(?prefLabel) || BOUND(?rdfsLabel))
}
ORDER BY ?label
"""

    rows = pinkkb.query(query)

    def jsonld_term(label: str) -> str:
        """Convert a label into a conservative JSON-LD term."""
        term = unicodedata.normalize("NFKD", label)
        term = term.encode("ascii", "ignore").decode("ascii")
        term = re.sub(r"[^A-Za-z0-9_-]+", "_", term)
        term = term.strip("_-")

        # Avoid JSON-LD keywords and ambiguous leading characters.
        if term.startswith("@") or term[0].isdigit():
            term = f"Class_{term}"

        return term


    classes = {"@context":{}}
    
    for class_iri, label in rows:
        name = jsonld_term(str(label))

        # Prevent two normalized labels from silently overwriting each other.
        if name in classes and classes[name]["@id"] != class_iri:
            suffix = hashlib.sha1(
                str(class_iri).encode("utf-8")
            ).hexdigest()[:8]
            name = f"{name}_{suffix}"

        classes["@context"][name] = {
            "@id": str(class_iri),
            "@type": OWL.Class,
        }
    
    return classes




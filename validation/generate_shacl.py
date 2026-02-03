"""
Generate SHACL shapes from PINK ontology for Dataset validation.

This script loads ontology files from onto/, extracts class hierarchy
and property constraints, and generates SHACL shapes with inheritance.
"""
from pathlib import Path
from typing import List, Optional, Tuple

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib import RDF, RDFS, OWL, XSD


# Namespace definitions
PINK = Namespace("https://w3id.org/pink#")
DDOC = Namespace("https://w3id.org/emmo/application/datadoc#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SH = Namespace("http://www.w3.org/ns/shacl#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")

# Class hierarchy for Dataset (bottom-up)
# pink:Dataset rdfs:subClassOf pink:Data rdfs:subClassOf prov:Entity
# dcat:Resource rdfs:subClassOf prov:Entity
DATASET_HIERARCHY = (
    DCAT.Resource,
    PINK.Data,
    PINK.Dataset,
)

# Shape URIs matching class hierarchy
SHAPE_URIS = {
    DCAT.Resource: PINK.ResourceShape,
    PINK.Data: PINK.DataShape,
    PINK.Dataset: PINK.DatasetShape,
}


def load_ontology(onto_dir: Path) -> Graph:
    """
    Load all TTL files from ontology directory into a single graph.

    Skips files with parse errors and prints warnings.

    Parameters:
        onto_dir: Path to directory containing .ttl files.

    Returns:
        Combined RDF graph with all ontology triples.
    """
    graph = Graph()
    for ttl_file in onto_dir.glob("*.ttl"):
        try:
            graph.parse(ttl_file, format="turtle")
            print(f"  Loaded: {ttl_file.name}")
        except Exception as e:
            print(f"  Warning: Skipping {ttl_file.name} (parse error: {e})")
    return graph


def get_properties_for_class(
    graph: Graph,
    target_class: URIRef
) -> List[Tuple[URIRef, URIRef, Optional[URIRef]]]:
    """
    Find properties with rdfs:domain matching target class and ddoc:conformance set.

    Parameters:
        graph: Ontology graph.
        target_class: Class URI to find properties for.

    Returns:
        List of tuples (property_uri, conformance_level, range_uri or None).
    """
    query = """
    SELECT DISTINCT ?prop ?conformance ?range
    WHERE {
        ?prop rdfs:domain ?domain .
        ?prop ddoc:conformance ?conformance .
        OPTIONAL { ?prop rdfs:range ?range . }
        FILTER (?domain = ?target)
    }
    """
    results = graph.query(
        query,
        initNs={"rdfs": RDFS, "ddoc": DDOC},
        initBindings={"target": target_class}
    )
    return [
        (URIRef(row.prop), URIRef(row.conformance), URIRef(row.range) if row.range else None)  # type: ignore[union-attr]
        for row in results
    ]


def get_annotation_properties_for_class(
    graph: Graph,
    target_class: URIRef
) -> List[Tuple[URIRef, URIRef, Optional[URIRef]]]:
    """
    Find annotation properties with rdfs:domain matching target class.

    Some properties like dcterms:title are annotation properties.

    Parameters:
        graph: Ontology graph.
        target_class: Class URI to find properties for.

    Returns:
        List of tuples (property_uri, conformance_level, range_uri or None).
    """
    query = """
    SELECT DISTINCT ?prop ?conformance ?range
    WHERE {
        ?prop a owl:AnnotationProperty .
        ?prop rdfs:domain ?domain .
        ?prop ddoc:conformance ?conformance .
        OPTIONAL { ?prop rdfs:range ?range . }
        FILTER (?domain = ?target)
    }
    """
    results = graph.query(
        query,
        initNs={"rdfs": RDFS, "ddoc": DDOC, "owl": OWL},
        initBindings={"target": target_class}
    )
    return [
        (URIRef(row.prop), URIRef(row.conformance), URIRef(row.range) if row.range else None)  # type: ignore[union-attr]
        for row in results
    ]


def is_datatype(range_uri: Optional[URIRef]) -> bool:
    """
    Check if range URI is an XSD datatype.

    Parameters:
        range_uri: The range URI to check.

    Returns:
        True if it's an XSD datatype.
    """
    if range_uri is None:
        return False
    return str(range_uri).startswith(str(XSD)) or str(range_uri) == str(RDF.langString)


def create_property_shape(
    shapes_graph: Graph,
    prop_uri: URIRef,
    conformance: URIRef,
    range_uri: Optional[URIRef]
) -> BNode:
    """
    Create a sh:property blank node for a property constraint.

    Parameters:
        shapes_graph: Graph to add triples to.
        prop_uri: Property URI (sh:path).
        conformance: Conformance level (mandatory/recommended/optional).
        range_uri: Range of property (for sh:class or sh:datatype).

    Returns:
        Blank node representing the property shape.
    """
    prop_shape = BNode()
    shapes_graph.add((prop_shape, SH.path, prop_uri))

    # Set cardinality based on conformance
    if conformance == DDOC.mandatory:
        shapes_graph.add((prop_shape, SH.minCount, Literal(1)))
    elif conformance == DDOC.recommended:
        # Add as warning severity
        shapes_graph.add((prop_shape, SH.severity, SH.Warning))

    # Set type constraint from range
    if range_uri is not None:
        if is_datatype(range_uri):
            shapes_graph.add((prop_shape, SH.datatype, range_uri))
        else:
            shapes_graph.add((prop_shape, SH["class"], range_uri))

    return prop_shape


def generate_shapes(onto_dir: Path, output_path: Path) -> None:
    """
    Generate SHACL shapes for Dataset class hierarchy.

    Creates shapes with sh:node inheritance mirroring class hierarchy.
    Properties are assigned to shapes based on rdfs:domain.

    Parameters:
        onto_dir: Path to ontology directory.
        output_path: Path to write shapes.ttl.
    """
    ontology = load_ontology(onto_dir)
    shapes = Graph()

    # Bind namespaces for readable output
    shapes.bind("sh", SH)
    shapes.bind("pink", PINK)
    shapes.bind("dcat", DCAT)
    shapes.bind("dcterms", DCTERMS)
    shapes.bind("xsd", XSD)
    shapes.bind("rdf", RDF)
    shapes.bind("skos", SKOS)
    shapes.bind("foaf", FOAF)
    shapes.bind("prov", PROV)

    # Generate shape for each class in hierarchy
    for i, target_class in enumerate(DATASET_HIERARCHY):
        shape_uri = SHAPE_URIS[target_class]

        # Declare as NodeShape
        shapes.add((shape_uri, RDF.type, SH.NodeShape))
        shapes.add((shape_uri, SH.targetClass, target_class))

        # Add inheritance from parent shape (except for root)
        if i > 0:
            parent_class = DATASET_HIERARCHY[i - 1]
            parent_shape = SHAPE_URIS[parent_class]
            shapes.add((shape_uri, SH.node, parent_shape))

        # Get object/datatype properties for this class
        properties = get_properties_for_class(ontology, target_class)

        # Get annotation properties for this class
        annotation_props = get_annotation_properties_for_class(ontology, target_class)
        properties.extend(annotation_props)

        # Create property shapes
        for prop_uri, conformance, range_uri in properties:
            prop_shape = create_property_shape(
                shapes, prop_uri, conformance, range_uri
            )
            shapes.add((shape_uri, SH.property, prop_shape))

    # Write shapes to file
    shapes.serialize(output_path, format="turtle")
    print(f"Generated SHACL shapes: {output_path}")
    print(f"  Classes: {[str(c).split('#')[-1] for c in DATASET_HIERARCHY]}")


def main() -> None:
    """Generate shapes from ontology in ../onto/ directory."""
    script_dir = Path(__file__).parent
    onto_dir = script_dir.parent
    output_path = script_dir / "shapes.ttl"

    generate_shapes(onto_dir, output_path)


if __name__ == "__main__":
    main()

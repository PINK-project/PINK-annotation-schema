"""
Generate SHACL shapes from PINK ontology for validation.

This script loads ontology files, discovers all classes dynamically,
extracts class hierarchy and property constraints, and generates
SHACL shapes with inheritance for comprehensive validation.
"""
from pathlib import Path
from dataclasses import dataclass, field

from typing import Dict, List, Optional, Tuple, Set

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib import RDF, RDFS, OWL, XSD
from rdflib.namespace import split_uri


# Namespace definitions
PINK = Namespace("https://w3id.org/pink#")
DDOC = Namespace("https://w3id.org/emmo/application/datadoc#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCTERMS = Namespace("http://purl.org/dc/terms/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SH = Namespace("http://www.w3.org/ns/shacl#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
PROV = Namespace("http://www.w3.org/ns/prov#")
EMMO = Namespace("https://w3id.org/emmo#")

# Namespaces to include for shape generation
# Classes from these namespaces will have shapes generated
TARGET_NAMESPACES = [
    str(PINK),
    str(EMMO),
    str(PROV),
    str(DCAT),
    str(FOAF),
    str(DCTERMS),
    str(SKOS),
]


def get_namespace(uri: URIRef) -> str:
    """Extract namespace from URI."""
    return split_uri(uri)[0]


def get_local_name(uri: URIRef) -> str:
    """Extract local name from URI."""
    return split_uri(uri)[1]


def generate_shape_uri(class_uri: URIRef) -> URIRef:
    """
    Generate a shape URI for a given class.

    Uses PINK namespace for all shapes with format: ClassNameShape

    Parameters:
        class_uri: The class URI to generate a shape for.

    Returns:
        Shape URI in PINK namespace.
    """
    local_name = get_local_name(class_uri)
    return PINK[f"{local_name}Shape"]


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


def discover_classes(graph: Graph) -> List[URIRef]:
    """
    Discover all owl:Class definitions in the ontology.

    Filters to only include classes from TARGET_NAMESPACES.

    Parameters:
        graph: Ontology graph.

    Returns:
        List of class URIs.
    """
    classes = []
    for cls in graph.subjects(RDF.type, OWL.Class):
        if isinstance(cls, URIRef):
            ns = get_namespace(cls)
            if ns in TARGET_NAMESPACES:
                classes.append(cls)
    return classes


def get_superclasses(graph: Graph, cls: URIRef) -> List[URIRef]:
    """
    Get direct superclasses of a class.

    Parameters:
        graph: Ontology graph.
        cls: Class URI.

    Returns:
        List of superclass URIs.
    """
    superclasses = []
    for parent in graph.objects(cls, RDFS.subClassOf):
        if isinstance(parent, URIRef):
            superclasses.append(parent)
    return superclasses


def topological_sort_classes(
    graph: Graph,
    classes: List[URIRef]
) -> List[URIRef]:
    """
    Sort classes so that parent classes come before children.

    Uses Kahn's algorithm for topological sorting.

    Parameters:
        graph: Ontology graph.
        classes: List of class URIs to sort.

    Returns:
        Topologically sorted list of class URIs.
    """
    class_set = set(classes)

    # Build dependency graph: child -> parents (within our class set)
    in_degree: Dict[URIRef, int] = {cls: 0 for cls in classes}
    children: Dict[URIRef, List[URIRef]] = {cls: [] for cls in classes}

    for cls in classes:
        for parent in get_superclasses(graph, cls):
            if parent in class_set:
                in_degree[cls] += 1
                children[parent].append(cls)

    # Start with classes that have no parents in our set
    queue = [cls for cls in classes if in_degree[cls] == 0]
    sorted_classes = []

    while queue:
        # Sort queue for deterministic output
        queue.sort(key=str)
        cls = queue.pop(0)
        sorted_classes.append(cls)

        for child in children[cls]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    # Handle any remaining classes (cycles or missing parents)
    remaining = [cls for cls in classes if cls not in sorted_classes]
    remaining.sort(key=str)
    sorted_classes.extend(remaining)

    return sorted_classes


@dataclass
class PropertyConstraints:
    """Aggregated constraints for a property from multiple sources."""
    prop_uri: URIRef
    conformance: Optional[URIRef] = None
    range_uri: Optional[URIRef] = None
    value_constraints: Set[URIRef] = field(default_factory=set)
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None

    def merge_from_restriction(self, range_uri: Optional[URIRef],
                               min_card: Optional[int] = None,
                               max_card: Optional[int] = None) -> None:
        """Merge constraints from OWL restriction."""
        if range_uri:
            self.value_constraints.add(range_uri)
            # Use restriction range if domain-based range not set
            if not self.range_uri:
                self.range_uri = range_uri

        if min_card is not None:
            self.min_cardinality = min_card
        if max_card is not None:
            self.max_cardinality = max_card


def get_properties_for_class(
    graph: Graph,
    target_class: URIRef
) -> List[Tuple[URIRef, Optional[URIRef], Optional[URIRef]]]:
    """
    Find properties with rdfs:domain matching target class.

    Includes properties with and without ddoc:conformance set.

    Parameters:
        graph: Ontology graph.
        target_class: Class URI to find properties for.

    Returns:
        List of tuples (property_uri, conformance_level or None, range_uri or None).
    """
    query = """
    SELECT DISTINCT ?prop ?conformance ?range
    WHERE {
        ?prop rdfs:domain ?domain .
        OPTIONAL { ?prop ddoc:conformance ?conformance . }
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
        (
            URIRef(row.prop),  # type: ignore[union-attr]
            URIRef(row.conformance) if row.conformance else None,  # type: ignore[union-attr]
            URIRef(row.range) if row.range else None  # type: ignore[union-attr]
        )
        for row in results
    ]


def get_restriction_properties_for_class(
    graph: Graph,
    target_class: URIRef
) -> List[Tuple[URIRef, Optional[URIRef], Optional[int], Optional[int]]]:
    """
    Find properties constrained via OWL restrictions on the class.

    Extracts property constraints from anonymous restriction blank nodes
    in rdfs:subClassOf statements.

    Parameters:
        graph: Ontology graph.
        target_class: Class URI to find restrictions for.

    Returns:
        List of tuples (property_uri, value_constraint, min_cardinality, max_cardinality).
    """
    query = """
    SELECT DISTINCT ?prop ?valueConstraint ?minCard ?maxCard ?exactCard ?hasSome
    WHERE {
        ?class rdfs:subClassOf ?restriction .
        ?restriction a owl:Restriction ;
                     owl:onProperty ?prop .

        # Value constraints (someValuesFrom, allValuesFrom)
        OPTIONAL {
            ?restriction owl:someValuesFrom ?valueConstraint .
            BIND(true AS ?hasSome)
        }
        OPTIONAL { ?restriction owl:allValuesFrom ?valueConstraint . }

        # Cardinality constraints
        OPTIONAL { ?restriction owl:minCardinality ?minCard . }
        OPTIONAL { ?restriction owl:maxCardinality ?maxCard . }
        OPTIONAL { ?restriction owl:cardinality ?exactCard . }
        OPTIONAL { ?restriction owl:minQualifiedCardinality ?minCard . }
        OPTIONAL { ?restriction owl:maxQualifiedCardinality ?maxCard . }
        OPTIONAL { ?restriction owl:qualifiedCardinality ?exactCard . }

        FILTER (?class = ?target)
    }
    """
    results = graph.query(
        query,
        initNs={"rdfs": RDFS, "owl": OWL},
        initBindings={"target": target_class}
    )

    restrictions = []
    for row in results:
        prop = URIRef(row.prop)  # type: ignore[union-attr]
        value_constraint = URIRef(row.valueConstraint) if row.valueConstraint else None  # type: ignore[union-attr]

        # Handle cardinality
        min_card = None
        max_card = None

        if row.exactCard is not None:  # type: ignore[union-attr]
            # owl:cardinality sets both min and max
            exact = int(row.exactCard)  # type: ignore[union-attr]
            min_card = exact
            max_card = exact
        else:
            if row.minCard is not None:  # type: ignore[union-attr]
                min_card = int(row.minCard)  # type: ignore[union-attr]
            if row.maxCard is not None:  # type: ignore[union-attr]
                max_card = int(row.maxCard)  # type: ignore[union-attr]

        # someValuesFrom implies at least one value
        if value_constraint and row.hasSome and not min_card:  # type: ignore[union-attr]
            min_card = 1

        restrictions.append((prop, value_constraint, min_card, max_card))

    return restrictions


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
    constraints: PropertyConstraints
) -> BNode:
    """
    Create a sh:property blank node for a property constraint.

    Properties without conformance are treated as optional (no sh:minCount).

    Parameters:
        shapes_graph: Graph to add triples to.
        constraints: Aggregated property constraints.

    Returns:
        Blank node representing the property shape.
    """
    prop_shape = BNode()
    shapes_graph.add((prop_shape, SH.path, constraints.prop_uri))

    # Set cardinality based on conformance or restriction cardinality
    # Restriction cardinality takes precedence
    if constraints.min_cardinality is not None:
        shapes_graph.add((prop_shape, SH.minCount, Literal(constraints.min_cardinality)))
    elif constraints.conformance == DDOC.mandatory:
        shapes_graph.add((prop_shape, SH.minCount, Literal(1)))

    if constraints.max_cardinality is not None:
        shapes_graph.add((prop_shape, SH.maxCount, Literal(constraints.max_cardinality)))

    # Set severity for recommended properties (if no explicit cardinality)
    if constraints.conformance == DDOC.recommended and constraints.min_cardinality is None:
        shapes_graph.add((prop_shape, SH.severity, SH.Warning))

    # Set type constraint from range
    if constraints.range_uri is not None:
        if is_datatype(constraints.range_uri):
            shapes_graph.add((prop_shape, SH.datatype, constraints.range_uri))
        else:
            shapes_graph.add((prop_shape, SH["class"], constraints.range_uri))

    return prop_shape


def generate_shapes(onto_dir: Path, output_path: Path) -> None:
    """
    Generate SHACL shapes for all classes in the ontology.

    Dynamically discovers all classes from TARGET_NAMESPACES,
    creates shapes with sh:node inheritance mirroring class hierarchy.
    Properties are assigned to shapes based on:
    - rdfs:domain declarations
    - OWL restrictions (owl:someValuesFrom, owl:allValuesFrom, cardinalities)

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
    shapes.bind("emmo", EMMO)

    # Discover and sort classes
    all_classes = discover_classes(ontology)
    sorted_classes = topological_sort_classes(ontology, all_classes)

    print(f"  Discovered {len(sorted_classes)} classes")

    # Track generated shapes for inheritance
    generated_shapes: Dict[URIRef, URIRef] = {}

    # Generate shape for each class
    for target_class in sorted_classes:
        shape_uri = generate_shape_uri(target_class)

        # Declare as NodeShape
        shapes.add((shape_uri, RDF.type, SH.NodeShape))
        shapes.add((shape_uri, SH.targetClass, target_class))

        # Add inheritance from parent shapes
        for parent_class in get_superclasses(ontology, target_class):
            if parent_class in generated_shapes:
                parent_shape = generated_shapes[parent_class]
                shapes.add((shape_uri, SH.node, parent_shape))

        # Get properties from rdfs:domain
        # domain_properties = get_properties_for_class(ontology, target_class)

        # Get properties from OWL restrictions
        # restriction_properties = get_restriction_properties_for_class(ontology, target_class)

        # Merge constraints by property URI
        # property_constraints: Dict[URIRef, PropertyConstraints] = {}

        # Add domain-based properties
        # for prop_uri, conformance, range_uri in domain_properties:
        #    property_constraints[prop_uri] = PropertyConstraints(
        #        prop_uri=prop_uri,
        #        conformance=conformance,
        #        range_uri=range_uri
        #    )

        # Merge restriction-based constraints
        # for prop_uri, value_constraint, min_card, max_card in restriction_properties:
        #    if prop_uri not in property_constraints:
        #        property_constraints[prop_uri] = PropertyConstraints(prop_uri=prop_uri)
        #
        #    property_constraints[prop_uri].merge_from_restriction(
        #        value_constraint, min_card, max_card
        #    )

        # Create property shapes
        # for constraints in property_constraints.values():
        #   prop_shape = create_property_shape(shapes, constraints)
        #    shapes.add((shape_uri, SH.property, prop_shape))

        # Track this shape for child class inheritance
        generated_shapes[target_class] = shape_uri

    # Write shapes to file
    shapes.serialize(output_path, format="turtle")
    print(f"Generated SHACL shapes: {output_path}")
    print(f"  Total shapes: {len(sorted_classes)}")


def main() -> None:
    """Generate shapes from ontology in ../onto/ directory."""
    script_dir = Path(__file__).parent
    onto_dir = script_dir.parent
    output_path = script_dir / "shapes.ttl"

    generate_shapes(onto_dir, output_path)


if __name__ == "__main__":
    main()

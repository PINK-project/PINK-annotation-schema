# The PINK Annotation Schema
The PINK Annotation Schema provides semantic annotations for the Safe and Sustainable by Design (SSbD) approach to guide the innovation process for chemicals and materials.
It adhears to the recommendations specified by [DCAT-AP 3.0.1] as implemented in [Tripper],
and builds on [PROV-O] for provenance.
It is constructed to be easily aligned with [EMMO].

> [!WARNING]
> The PINK Annotation Schema is still under early and heavy development and may change without notice.
> It is not intended for production at the current stage.


## Repository Files
- `catalog-v001.xml`: XML catalog mapping ontology files to their IRIs for semantic web tools.
- `contributors.ttl`: Turtle file listing contributors to the PINK Annotation Schema for this repository.
- `pink_annotation_schema.ttl`: Main ontology file for the PINK Annotation Schema.
- `reused-terms.ttl`: Terms from standard vocabularies reused by the schema.
- `LICENSE`: Creative Commons Attribution 4.0 International license.
- `docs/`: Sub-directory with documentation.


## Extra PINK annotations of externally defined terms
The PINK Annotation Schema never changes the semantics of existing terms defined externally (e.g. by W3C or DCAT-AP).
However, the PINK Annotation Schema can:
- Make the documentation of externally defined terms explicit in the Knowledge Base (KB) without importing the whole vocabularies.
- Add PINK-specific usage notes (using `pink:usageNote`, not `vann:usageNote`).
- Add a `ddoc:conformance` relation that specifies whether the relation is "mandatory", "recommended" or "optional" in PINK.
  PINK will never change the conformance described in the DCAT-AP documentation to something weaker.

The basic rule for such additions is that they can live hand-in-hand with similar annotations by other projects without creating confusion or inconsistencies.

For any other additional specifications of an existing term, a PINK-specific subclass or subproperty will be created.
Such subclasses/subproperties will normally keep the W3C name, but with the `pink` namespace (or the `ddoc` namespace if the concept is specific for the tripper data documentation).



## Taxonomy
The taxonomy below shows a basic categorisation of the main concepts (OWL classes) in the PINK Annotation Schema.
It unifies concepts from common vocabularies, like [Dublin Core], [DCAT], [PROV-O] and [FOAF].
This gives the adapted terms additional context.
However, the taxonomy is intentionally weekly axiomated in order to facilitate alignment to different popular top-level ontologies, like [EMMO], [DOLCE] and [BFO].


![Taxonomy](docs/figs/taxonomy.png)

At the top-level, the PINK Annotation Schema has four root concepts:

- **`prov:Entity`**: A physical, digital, conceptual, or other kind of thing with some fixed aspects.
  [PROV-O] lacks the accuracy of nominalism and allows both real and imaginary entities.

- **`prov:Activity`**: Something that occurs over a period of time and acts upon or with entities.
  Hence, its individuals have some temporal parts (that are not of the same type as the activity itself).
  An activity may include consuming, processing, transforming, modifying, relocating, using, or generating entities.

- **`:Role`**: The class of all individuals that are defined through a parthood relation to an entity.
  The individual can be said to have a *role* in relation to the entity.

- **`foaf:Agent`**: A thing that does stuff (like person, group, software or physical artifact).
  The [FOAF] specification of a *agent* is very loose.
  The subclass `prov:Agent` provides further context, by saying that a `prov:agent` bears some form of responsibility for an activity, the existence of an entity or the activity of another agent.

See the [PINK classes] table and the PINK Annotation Schema itself, for a description of all the other concepts.


## Provenance
The provenance description in PINK is based on [PROV-O].

For more accurate descriptions of complex workflows involving spatial and temporal parts, PINK suggests an enhanced formalism.

A textual description of the provenance can be provided with `dcterms:provenance`.
However, for a semantic provenance description [PROV-O] should be used (since `dcterms:provenance` has no agreed semantics as discussed by [DCAT-AP][dcatap-provenance]).

The basic building block of a provenance description is a `prov:Activity` with `prov:Entity` as input and output:

![General activity](docs/figs/general-activity.png)

As shown in the taxonomy, this general process can be sub-categorised according to its input and output:

![Categorised activities](docs/figs/categorised-activities.png)

Traceability can be achieved by connecting a series (or network) of these basic building blocks.
<!-- When two or more intentionally planned processes are connected this way, we call it a *workflow*. -->
By providing additional knowledge to the various process steps we get *provenance*.
The figure below shows an example of a simple provenance graph, that combines three processes with some additional annotations.

![Provenance](docs/figs/provenance.png)


Concepts belonging to the PINK namespace in the figure above have been written in cursive.

Given the network of `:used` and `:wasInformedBy` relations, it is possible to infer `:wasInformedBy` and `:wasDerivedFrom` relations.
This is done by the reasoner (using [SWRL] rules that are added in the pink_annotation_schema.ttl).



### Complex workflows with spatial and temporal parts
An important aspect of provenance is to keep track on how a sample e.g. is cut into several specimens and how the specimens later may be joined in new configurations.
Likewise, how a material is changed during a process or part of a process.

The figure below shows a material process (`p`) that changes a material (`m`).
The input and output of the material process are the temporal parts (`m1` and `m2`) of the material, respectively.
The material process is driven by an agent (`a`), who's temporal part (`a1`) is a participant (i.e. has an active role) in the process.

![Material process](docs/figs/material-process.png)


### Enhanced parthood and causal formalism
To formally describe workflows correctly, such as the above material process, the PINK Annotation Schema includes formalised categorisations of parthood and causal relations, shown in the figures below.
These categorisations incorporate parthood and causal relations from [Dublin Core] and [PROV-O] and give them enhanced semantic meaning.

![Parthood relations](docs/figs/parthood-relations.png)

For improved semantic expressiveness and to support logical validation, the PINK Annotation Schema adds characteristics to the standard [PROV-O] object properties.
According to the [rules](#extra-pink-annotations-of-externally-defined-terms) defined above, the characteristics is added to PINK-specific subproperties of the [PROV-O] object properties.
Such semantically enhanced subclass relations of corresponding [PROV-O] and [Dublin Core] relations are written in *cursive* in the figure above.

> [!TIP]
> Object property chracteristics is explained in the [Protégé documentation](https://protegeproject.github.io/protege/views/object-property-characteristics/).
>
> Antisymmetric (not included in OWL) is a weaker form of asymmetric: if `x -> y`, then `y -> x` if and only if `x = y`.
> This is not the case for asymmetric relations, since they exclude the equality `x = y`.

![Causal relations](docs/figs/causal-relations.png)


### Property relations
The PINK Annotation Schema includes currently one relation that is neither a parthood nor a causal relation.
This is the `:hasProperty` relation that connects an entity or activity to one of its properties (via a [semiotic] process involving an interpreter that assigns the property).
The most important feature of `:hasProperty` is that it adhere to the scientific view that a property is not an intrinsic quality of an entity, but something that is measured or determined by an interpreter.

For example, to determine the toxicity of a chemical substance you have to measure (or calculate or estimate) it. And the result depends on how it is measured.

![Property relations](docs/figs/property-relations.png)



## General description of methods
Provenance is about what has happened. [PROV-O] is intended to describe provenance information.
In PINK we also want to describe general workflows before they are executed.
That is, to describe something that can happen.

Since we don't know whether the workflow actually would be executed, we can't create individuals for it.
Hence, description of what can happen must be done at class level (TBox-level).

Another important difference from the provenance description above, is that while provenance places the activity in the centre, PINK places the *method* in centre when describing something that can happen.
A method is data that describes how to perform an activity, like what type of activity will be performed, what type of input it takes, what type of output it produces, is there an API for performing the activity, etc...
The figure below shows how a method relates to an Activity and its input and output.

![Method](docs/figs/method.png)

In Manchester syntax, this may be expressed as follows

    Class: app:MyMethod
        subClassOf: pink:Method
        subClassOf: pink:isMethodOf some app:MyActivity
        subClassOf: pink:input some app:MyInput
        subClassOf: pink:output some app:MyOutput

where `app` is the prefix of the application ontology defining the method and its associated activity and input/output.

PINK provides tooling (based on [Tripper]) to help providing class-level documentation.
This is done the normal way using spreadsheets, but with the `@type` keyword replaced by `subClassOf` (`@type` is implicit and would always be `owl:Class`).
For example, the above declaration of a computation could provided as follows:

| @id               | subClassOf       | description | isMethodOf     | input       | output       |
|-------------------|------------------|-------------|----------------|-------------|--------------|
| app:MyComputation | pink:Computation | ...         | app:MyActivity | app:MyInput | app:MyOutput |




[PINK classes]: ./docs/classes.md
[semiotic]: https://plato.stanford.edu/entries/peirce-semiotics/
[DCAT-AP 3.0.1]: https://semiceu.github.io/DCAT-AP/releases/3.0.1/
[DCAT]: https://www.w3.org/TR/vocab-dcat-3/
[FOAF]: http://xmlns.com/foaf/spec/
[PROV-O]: https://www.w3.org/TR/prov-o/
[Dublin Core]: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
[dcatap-provenance]: https://interoperable-europe.ec.europa.eu/collection/semic-support-centre/solution/dcat-application-profile-implementation-guidelines/release-5
[SWRL]: https://www.w3.org/submissions/SWRL/
[EMMO]: https://emmc.eu/emmo/
[DOLCE]:https://www.loa.istc.cnr.it/dolce/overview.html
[BFO]: https://basic-formal-ontology.org/
[Tripper]: https://emmc-asbl.github.io/tripper/latest/

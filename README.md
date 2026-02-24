# The PINK Annotation Schema
The PINK Annotation Schema provides semantic annotations for the Safe and Sustainable by Design (SSbD) approach to guide the innovation process for chemicals and materials.
It adhears to the recommendations specified by [DCAT-AP 3.0.1] as implemented in [Tripper],
and builds on [PROV-O] for provenance.
It is constructed to be easily aligned with [EMMO].

> [!WARNING]
> The PINK Annotation Schema is still under development and may change without notice.
> It is not intended for production at the current stage.


## Resources
- [Theoretical background].
  - [Background], including handling of [provenance] and categorisation of relations into [parthood], [causal] and [semiotic] relations.
  - Documentation of sub-modules:
    - [Matter module]
    - [Models module]
  - [Class-level] documentation
- Reference documentation with interlinked definitions of classes and properties for:
  - [PINK Annotation Schema].
  - [Reused terms], i.e. terms reused from existing vocabularies (e.g. [PROV-O], [DCAT-AP 3.0.1]).
  - [Matter], including categorisation of substances, materials, molecules, etc...
  - [Models], including categorisation of statistical, physics and data-based (AI) models.
  - [CHEMINF descriptors], a taxonomy of descriptors from mainly the chemistry domain
- [Guiding principles] for the implementation of the PINK Annotation Schema
- [Turtle file] including all imported concepts (source of truth).
- [Inferred turtle file] reasoned with HermiT.


## Top level taxonomy
The taxonomy below shows a basic categorisation of the main concepts (OWL classes) in the PINK Annotation Schema.
It unifies concepts from common vocabularies, like [Dublin Core], [PROV-O], [DCAT] and [FOAF].
This gives the adapted terms additional context.
However, the taxonomy is intentionally weekly axiomated in order to facilitate alignment to different popular top-level ontologies, like [EMMO], [DOLCE] and [BFO].

![Taxonomy](docs/figs/taxonomy.svg)


## Usage example
The example below shows how one can document a toxicity computation using the PINK Annotation Schema.

![Paracetamol-example](docs/figs/paracetamol-example.svg)



[Theoretical background]: https://pink-project.github.io/PINK-annotation-schema/docs/
[Background]: https://pink-project.github.io/PINK-annotation-schema/docs/background.html
[provenance]: https://pink-project.github.io/PINK-annotation-schema/docs/background.html
[parthood]: https://pink-project.github.io/PINK-annotation-schema/docs/background.html#parthood-relations
[causal]: https://pink-project.github.io/PINK-annotation-schema/docs/background.html#causal-relations
[semiotic]: https://pink-project.github.io/PINK-annotation-schema/docs/background.html#semiotic-relations
[Class-level]: https://pink-project.github.io/PINK-annotation-schema/docs/background.html#class-level-documentation
[Guiding principles]: https://pink-project.github.io/PINK-annotation-schema/docs/guiding-principles.html
[Matter module]: https://pink-project.github.io/PINK-annotation-schema/docs/matter.html
[Models module]: https://pink-project.github.io/PINK-annotation-schema/docs/models.html

[PINK Annotation Schema]: https://pink-project.github.io/PINK-annotation-schema/widoco/index-en.html
[Reused terms]: https://pink-project.github.io/PINK-annotation-schema/widoco-reused-terms/index-en.html
[Matter]: https://pink-project.github.io/PINK-annotation-schema/widoco-matter/index-en.html
[Models]: https://pink-project.github.io/PINK-annotation-schema/widoco-models/index-en.html
[CHEMINF descriptors]: https://pink-project.github.io/PINK-annotation-schema/widoco-cheminf/index-en.html
[Turtle file]: https://pink-project.github.io/PINK-annotation-schema/pink_annotation_schema.ttl
[Inferred turtle file]: https://pink-project.github.io/PINK-annotation-schema/pink_annotation_schema-inferred.ttl

[PINK classes]: ./docs/classes.md
[pink_annotation_schema.ttl]: ./pink_annotation_schema.ttl
[Zaccarini *et. al.*]: https://ebooks.iospress.nl/doi/10.3233/FAIA231120
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

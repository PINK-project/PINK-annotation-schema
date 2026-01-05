# Tools

## Generating keywords file for Tripper
To generate the keywords file for [Tripper], run the file `scripts/generate_tripper_keywords.py`.

This requires that [Tripper] is installed in your python environment.

A few considerations when running the script:
First and foremost, when the keywords are generated from the ontology the argument `redefine` is set to `allow`.
This means that terms already defined in Tripper's default keywords will be overwritten if they match prefLabels in the PINK Annotation schema.
In addition, when turning on logging a few extra notifications are printed.
 - Missing classes, i.e. classes that are not already defined, are added in the Keywords. This happens for `http://www.w3.org/ns/prov#Entity` and `http://www.w3.org/ns/prov#Entity`.
 - `documentation` is redefined from `foaf:page` to `pink:documentation` because pink specifies that this is the documentation of a Resource. Note that pink:documentation is a subproperty of foaf:page.
 - `hasPart` is redefined from `dcterms:hasPart` to `pink:hasPart` because hasPart in pink is further refined to be a subproperty of `pink:overlaps`.
 - `conformance` is redefined from `ddoc:conformance` to `pink:conformance` because additional requirements are added in PINK on top of dcat-ap, which is the default in Tripper.
 - `wasGeneratedBy` is redefined from `prov:wasGeneratedBy` to `pink:wasGeneratedBy` because it is further refined in PINK as a subproperty of `prov:wasGeneratedBy`.

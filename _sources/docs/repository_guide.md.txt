# This document is intneded as support for the curators of the repository #

## Documentation setup ##

The `ontokit` tool avilable from EMMOntoPy was used to generate the standard documentation and workflows.
Note that the documentation and workflows are further refined according to the needs of the PINK-annotation-schema.


To generate the documentation locally please write the command
```bash
ontokit docs --imported --recursive .
```

Note that it was chosen to include imported ontologies recursively since the ontology does not explicitly import ontologies from
outside. Rather we are explicitly including all terms from other ontologies that we are including.
This might change in the future.

# Validation profiles

The documentation tables are validated against a *profile* for each type of resource.
A profile lists the properties that are expected for that type of resource,
whether each one must be given, and which values it accepts (its *range*).
The profiles are used by `prepare-tables` (see [Scripts](scripts.md)).

## Where to find them

The profiles are CSV files in the
[`profiles/`](https://github.com/PINK-project/PINK-annotation-schema/tree/main/profiles) folder of the repository,
one file for each resource type:

| Profile | Resource type | Used for |
|---------|---------------|----------|
| [`software.csv`](https://github.com/PINK-project/PINK-annotation-schema/blob/main/profiles/software.csv) | Software release (individual) | the software tab |
| [`computation.csv`](https://github.com/PINK-project/PINK-annotation-schema/blob/main/profiles/computation.csv) | Computation type (class) | the computation tab, and the computations made from the software tab |
| [`datasettype.csv`](https://github.com/PINK-project/PINK-annotation-schema/blob/main/profiles/datasettype.csv) | Dataset type (class) | the dataset type tab |
| [`dataset.csv`](https://github.com/PINK-project/PINK-annotation-schema/blob/main/profiles/dataset.csv) | Dataset (individual) | the dataset tab |
| [`agent.csv`](https://github.com/PINK-project/PINK-annotation-schema/blob/main/profiles/agent.csv) | Agent (individual) | people and organisations |

The current content of each profile is shown [at the bottom of this page](#the-profiles).
Another folder with profiles can be given to `prepare-tables` with `--profiles`.

## How they were made

The profiles are based on the matrix of
[expected annotations by resource type](https://ssbd-ontology.github.io/core/docs/document-your-data.html#expected-annotations-by-resource-type)
in the SSbD Core ontology documentation, which was agreed within the PINK project.
Each column of that matrix (Software release, Computation type, Dataset type, Dataset and Agent)
matches one profile:

- The **property** and **guidance** are taken from the matrix.
  The *value kind* of the matrix is not a separate column. It is covered by the range, and where
  it says more (e.g. that a licence is given as the IRI of the licence document), this is added to the guidance.
- The **condition** starts from the entry of the matrix for that resource type, where *Required* is written as `mandatory`.
  For some properties PINK is stricter than the matrix, e.g. `hasAPI` is mandatory for software
  and `title` is mandatory for computation types.
- The **range** is added for PINK, to tell the validation which values are accepted (see below).
  The range of a property is the same in all profiles, except for `curator`
  (only ORCIDs for software, ORCIDs or ROR IDs otherwise) and `subClassOf`
  (SSbD Core terms for computation types, any IRI for dataset types).

The profiles are maintained by hand: if the expected annotations in the SSbD Core documentation change,
the profiles must be updated accordingly.

## What the columns mean

| Column | Meaning |
|--------|---------|
| `property` | The tripper keyword of the property, as used in the column name of the prepared table. |
| `condition` | `mandatory`, `recommended`, `conditional` or `optional`. |
| `range` | Which values are accepted (see below). |
| `guidance` | How to fill in the property. |

The **condition** decides what happens when a value is missing:

| Condition | Missing column | Empty cell |
|-----------|----------------|------------|
| `mandatory` | Error (every row fails) | Error (the row fails) |
| `recommended` | Warning | Warning |
| `conditional` | not checked | not checked |
| `optional` | not checked | not checked |

Rows with errors are left out of the clean tables (and of the graph); rows with warnings are kept.

The **range** decides which values are accepted, whatever the condition.
It is one or more of the following, separated by `|`.
A value is accepted if it is in one of them, e.g. `orcid | ror` accepts an ORCID or a ROR ID.

### Predefined ranges

The predefined ranges are written in lower case.

| Range | Accepted values |
|-------|-----------------|
| `string` | Any text. |
| `boolean` | `Yes` or `No` (in any case), or a true/false cell. |
| `date`, `dateTime` | A date, or a date and time, in a common format (e.g. `2025-08-18` or `January 2015`). |
| `iri` | Any valid IRI. A prefix must be known (see below). |
| `url` | A resolvable `http://` or `https://` URL. A URL that needs a login gives a warning. |
| `orcid` | An ORCID, `https://orcid.org/XXXX-XXXX-XXXX-XXXX`, that exists. It is looked up at ORCID. |
| `ror` | A ROR ID, `https://ror.org/XXXXXXXXX`, that exists. It is looked up at ROR. |
| `ssbd` | A term in the SSbD Core ontology, including the terms it takes from other ontologies (e.g. `emmo:`). It may be given by its label. |
| `rights` | An access right from the [EU vocabulary on access rights](http://publications.europa.eu/resource/authority/access-right): `PUBLIC`, `NON_PUBLIC`, `RESTRICTED`, `CONFIDENTIAL` or `SENSITIVE`. The prefix `rights:` is added if it is left out. |
| `iana` | An IANA media type, e.g. `iana:application/zip`. Use `distribution.format` for a free-text format. |

`string`, `boolean`, `date` and `dateTime` are literals: they cannot be combined with other ranges.

### Ontology classes

A range can also be an ontology class with a known prefix, e.g. `ssbd:Model`.
A value is then accepted if it is that class, a subclass of it, or an individual of one of them.
For example, `ssbd:RandomForest` is accepted for `implementsModel` (range `ssbd:Model`),
but `emmo:Molecule` is not.

- The value is looked up in the SSbD Core ontology, including the terms it takes from other ontologies.
- A resource documented in the same spreadsheet is checked through its `@type` (an individual)
  or its `subClassOf` (a class). This is how a software release in the software tab
  is accepted for `hasSoftware` (range `ssbd:Software`).
- A value may be given by its label, e.g. `Random forest` for `ssbd:RandomForest`.
- A value of the wrong class, or a value that is neither in the ontology nor in the spreadsheet,
  is an error. For a value that is not found, a term with the same name but another prefix is suggested,
  if there is one.

The classes used in the profiles are `ssbd:Matter` (`chemicalClass`), `ssbd:Model` (`implementsModel`),
`ssbd:Property` (`outputsIndicator`), `ssbd:Software` (`hasSoftware`) and `ssbd:TierLevel` (`inTierLevel`).

### Prefixes

The known prefixes are those of the [SSbD context](https://w3id.org/ssbd/context/) and the PINK prefixes
(e.g. `pink:`, `pinksw:`, `datasettype:`). A value with an unknown prefix is an error.
A profile with an unknown range, a class with an unknown prefix, or a literal combined with another range
is reported when `prepare-tables` starts.

## The profiles

The tables below are read directly from the files in `profiles/`.

`````{tab-set}

````{tab-item} Software
```{csv-table}
:file: ../profiles/software.csv
:header-rows: 1
```
````

````{tab-item} Computation
```{csv-table}
:file: ../profiles/computation.csv
:header-rows: 1
```
````

````{tab-item} Dataset type
```{csv-table}
:file: ../profiles/datasettype.csv
:header-rows: 1
```
````

````{tab-item} Dataset
```{csv-table}
:file: ../profiles/dataset.csv
:header-rows: 1
```
````

````{tab-item} Agent
```{csv-table}
:file: ../profiles/agent.csv
:header-rows: 1
```
````

`````

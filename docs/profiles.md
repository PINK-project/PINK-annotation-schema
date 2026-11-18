# Validation profiles

The documentation tables are validated against a *profile* for each type of resource.
A profile lists the properties that are expected for that type of resource,
whether each one must be given, what kind of value it takes and, for IRIs, which IRIs are accepted.
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
  The *value kind* of the matrix is not a separate column: it is covered by the datatype and range,
  and where it says more (e.g. that a license is given as the IRI of the licence document), this is added to the guidance.
- The **condition** starts from the entry of the matrix for that resource type, where *Required* is written as `mandatory`.
  For some properties PINK is stricter than the matrix, e.g. `hasAPI` is mandatory for software
  and `title` is mandatory for computation types.
- The **datatype** and **range** are added for PINK, to tell the validation how a value is checked (see below).
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
| `datatype` | The kind of value: text, true/false, a date or an IRI (see below). |
| `range` | For IRIs: which IRIs are accepted (see below). Empty for other datatypes. |
| `guidance` | How to fill in the property. |

The **condition** decides what happens when a value is missing:

| Condition | Missing column | Empty cell |
|-----------|----------------|------------|
| `mandatory` | Error (every row fails) | Error (the row fails) |
| `recommended` | Warning | Warning |
| `conditional` | not checked | not checked |
| `optional` | not checked | not checked |

Rows with errors are left out of the clean tables (and of the graph); rows with warnings are kept.

The **datatype** says what kind of value is given, and how it is checked, whatever the condition:

| Datatype | Value | Check |
|----------|-------|-------|
| `xsd:string` | Text. | None. |
| `xsd:boolean` | `true` or `false`. | `yes` and `no` are also accepted, and translated. |
| `xsd:date`, `xsd:dateTime` | A date, or a date and time. | Must be readable as a date. |
| `IRI` | A link to a resource. | Must be a valid IRI, and in the range (see below). Known prefixes are expanded. |

The **range** says which IRIs are accepted for an `IRI` property.
It is one or more of the names below, separated by `|`.
A value is accepted if it is in one of them; an empty range accepts any valid IRI.

| Range | Accepts | Check |
|-------|---------|-------|
| `orcid` | An ORCID, `https://orcid.org/XXXX-XXXX-XXXX-XXXX`. | Looked up at orcid.org. |
| `ror` | A ROR ID, `https://ror.org/XXXXXXXXX`. | Looked up at ror.org. |
| `ssbd` | A term in the SSbD Core ontology, including the terms it takes from other ontologies (see below). | Looked up in the ontology; it may be given by its full IRI, with a prefix, or by its label. |
| `rights` | An access right from the [EU vocabulary on access rights](http://publications.europa.eu/resource/authority/access-right): `rights:PUBLIC`, `rights:RESTRICTED`, `rights:NON_PUBLIC`, `rights:CONFIDENTIAL` or `rights:SENSITIVE`. | Must be one of these. The prefix `rights:` may be left out. |
| `iana` | An IANA media type, e.g. `iana:application/zip`. | Must be an IRI. |
| `url` | A web address. | Must resolve. A URL that needs a login gives a warning. |

The SSbD Core ontology does not only contain terms in its own namespace (`ssbd:`).
It also includes terms from other ontologies, which keep their original IRIs,
e.g. `emmo:DataProcessing` from EMMO, `cheminf:CHEMINF_000159` from CHEMINF and `obo:CHEBI_23367` from ChEBI.
These are all accepted for the range `ssbd`, so the range means *in the SSbD Core ontology*,
not *in the `ssbd:` namespace*. Use the IRI that the term has in the ontology:
e.g. `emmo:DataProcessing`, not `ssbd:DataProcessing`. If the prefix is wrong, the error message suggests the right one.

For example, the curator of software must be a person, so its range is `orcid`,
while the creator may be a person or an organisation, so its range is `orcid | ror`:

```
property,condition,datatype,range,...
curator,mandatory,IRI,orcid,...
creator,recommended,IRI,orcid | ror,...
```

A ROR ID as curator of software gives an error, while it is accepted as creator.

To accept another kind of IRI, e.g. a new identifier scheme, a range is added to `RANGES`
in `src/pink/validateutils.py`, with a function that checks it.

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

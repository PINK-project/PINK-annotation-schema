# Validation profiles

The documentation tables are validated against a *profile* for each type of resource.
A profile lists the properties that are expected for that type of resource,
whether each one must be given, and what kind of value it takes.
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

- The **property**, **value kind** and **guidance** are taken from the matrix.
- The **condition** starts from the entry of the matrix for that resource type, where *Required* is written as `mandatory`.
  For some properties PINK is stricter than the matrix, e.g. `hasAPI` is mandatory for software
  and `title` is mandatory for computation types.
- The **datatype** is added for PINK, to tell the validation how a value is checked (see below).

The profiles are maintained by hand: if the expected annotations in the SSbD Core documentation change,
the profiles must be updated accordingly.

## What the columns mean

| Column | Meaning |
|--------|---------|
| `property` | The tripper keyword of the property, as used in the column name of the prepared table. |
| `condition` | `mandatory`, `recommended`, `conditional` or `optional`. |
| `datatype` | How a value is checked (see below). |
| `value_kind` | The kind of value expected, as described in the SSbD Core documentation. |
| `guidance` | How to fill in the property. |

The **condition** decides what happens when a value is missing:

| Condition | Missing column | Empty cell |
|-----------|----------------|------------|
| `mandatory` | Error (every row fails) | Error (the row fails) |
| `recommended` | Warning | Warning |
| `conditional` | not checked | not checked |
| `optional` | not checked | not checked |

Rows with errors are left out of the clean tables (and of the graph); rows with warnings are kept.

The **datatype** decides how a given value is checked, whatever the condition:

| Datatype | Check |
|----------|-------|
| `string` | Any text. |
| `IRI` | A valid IRI (with a known prefix). |
| `URL` | A resolvable IRI. A URL that needs a login gives a warning. |
| `boolean` | `true` or `false`. |
| `dateTime` | A date, or a date and time. |
| `SSbDCore` | An entry that exists in the SSbD Core ontology. It may be given by its label. |
| `AgentIRI` | A ROR or ORCID identifier. |
| `PersonIRI` | An ORCID identifier. |
| `MediaTypeIRI` | An IANA media type, e.g. `iana:application/zip`. |

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

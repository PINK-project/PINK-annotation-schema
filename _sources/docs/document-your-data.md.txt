# Tutorial on documenting your data using tables

This is a step-by-step guide to help you document your resource with the PINK Annotation Schema using table-based workflows (for example, Excel).

A resource is the thing you want to describe and share in a structured way.
In practice, a resource can be a dataset, a software tool, a workflow, a model, or another documented digital object. Note that a resource can be either a class (a concept) or an individual (a specific instance of a concept). That means that you can document a type of experiment or
simulation (a class) as well as a specific experiment or simulation (an individual).
The goal of this guide is to help you capture the key metadata for that resource in a clear and reusable format.

## Quick introduction to classes and individuals

When documenting data, we need to describe both classes (concepts of things) and individuals (actual instances of things).
For example, there is a difference between the concept of a pen and one specific pen.
If I ask my child to bring me a pen, I do not care which pen she brings, but she understands the concept and brings an actual individual pen.

<img src="https://pink-project.github.io/PINK-annotation-schema/docs/figs/concept_pen_cartoon.png" alt="Cartoon illustrating a request for a pen and the return of an individual pen" width="400"/>
Figure 1. Cartoon illustrating a request for a pen (concept) and the return of an individual pen. Image created partly with ChatGPT (OpenAI), 2026.

Similarly, we can ask for a specific type of simulation and it can be returned.
Even better we can connect various concepts together and for instance create
workflows that connects datasets and simulations.

<img src="https://pink-project.github.io/PINK-annotation-schema/docs/figs/connected_concepts.png" alt="Concepts of datasets and simulations can be connected together in a workflow because we have documented what the inputs and outputs of the various simulations are." width="400"/>
Figure 2. Concepts of datasets and simulations can be connected together in a workflow because
we have documented what the inputs and outputs of the various simulations are.  

## Documenting your resources in practice

In PINK we are documenting various resources. We are here presenting examples of how to document dataset types (as concepts), computation software (as individuals), indicators (as concepts), and computations (as concepts) with tables.

How to construct the tables:
- There is a column @id, which is the unique identifier for the resource.
  For classes, this is a URI that identifies the concept.
  For individuals, this is a URI that identifies the specific instance.
  (NB: in the google spread sheets this column is callsed identifier, but it is the same as @id. Please use @id in your own spreadsheets.).
- There is a column @type, which indicates whether the resource is a class or an individual, and
  also what kind of class or individual it is (for example, a dataset type, a software tool, etc.).
  If it is a class, the @type column should have the value owl:Class. If it is an individual, the @type column should have the concept that this individual is an instance of (for example, pink:Dataset, pink:Software, etc.).
- For classes, there is a column subClassOf, which indicates the parent class that this class is a
  subclass of.
  For individuals, there is no subClassOf column because individuals are not subclasses of anything.
- For both classes and individuals, there are columns for the properties that we want to document (for example, label, description, hasInput, hasOutput, etc.).
  The properties that we want to document depend on the type of resource we are documenting and the use case we have in mind.
  The Object Properties, Annotation Properties and Data Properties in the PINK Annotation Schema are a good starting point for deciding which properties to document for each resource.
  They can be found in the [Reference Documentation].
  (In the google spread sheets, the columns are filled with chosen properties.)
- The values in the table should be filled according to the definitions of the properties in the PINK Annotation Schema.
    - All annotation properties should be filled with a literal value (for example, a string or a number).
    - All object properties should be filled with a URI that identifies another resource (for example, a dataset type, a software tool, etc.). Here it is important to make sure that you refer to something within the correct range.

## Table templates

### 1. Dataset type table (class-level documentation)

| @id | label | description | subClassOf | theme | format | @type |
|---|---|---|---|---|---|---|
| datasettype:ToxicityDataset | Toxicity dataset | Dataset type for toxicity endpoints. | pink:DatasetType | pink:SafetyAndSustainability | text/csv | owl:Class |
| datasettype:ExposureDataset | Exposure dataset | Dataset type for exposure-related data. | pink:DatasetType | pink:SafetyAndSustainability | application/json | owl:Class |

### 2. Computation type table (class-level documentation)

| @id | title | hasInput | hasOutput | subClassOf | @type |
|---|---|---|---|---|---|
| pink:activity_qsar_prediction | QSAR prediction | datasettype:ToxicityDataset | datasettype:ToxicityDataset | pink:Computation | owl:Class |
| pink:activity_screening | Activity Screening | datasettype:ExposureDataset | datasettype:ToxicityDataset | pink:Computation | owl:Class |

### 3. Software table (individual documentation)

| @id | title | description | tierLevel | implementsModel | hasAPI | accessRights |
|---|---|---|---|---|---|---|
| pink:mytool-v1 | MyTool v1 | In-house software for endpoint prediction. | pink:Tier3 | pink:QSARModel | https://example.org/api/mytool | rights:PUBLIC |
| pink:mytool-v2 | MyTool v2 | Updated release with improved descriptors. | pink:Tier3 | pink:QSARModel | https://example.org/api/mytool/v2 | rights:RESTRICTED |

### 4. Agent table (individual documentation)

| @id | name | @type |
|---|---|---|
| https://orcid.org/0000-0000-0000-0001 | Example Researcher | prov:Agent |
| https://example.org/org/acme-lab | Acme Lab | prov:Agent |

### 5. Dataset table (individual documentation)

| @id | @type | dcterms:title | dcterms:description | dcterms:publisher |
|---|---|---|---|---|
| https://example.org/dataset/tox-001 | pink:Dataset | My toxicity dataset@en | Measurements from in vitro assay campaign.@en | https://orcid.org/0000-0000-0000-0001 |
| https://example.org/dataset/exposure-001 | pink:Dataset | My exposure dataset@en | Exposure observations collected in 2025.@en | https://example.org/org/acme-lab |


[Reference Documentation]: https://pink-project.github.io/PINK-annotation-schema/pink_annotation_schema.html

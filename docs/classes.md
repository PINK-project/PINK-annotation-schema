PINK Classes defined in the PINK Annotation Schema
==================================================


| IRI                  | Definition                                                                       | PINK usage note                                                                                           |
|----------------------|----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| prov:Entity          | A physical, digital, conceptual, or other kind of thing with some fixed aspects. | [PROV-O] lacks the accuracy of nominalism and allows both real and imaginary entities.                    |
| prov:Activity        | Something that occurs over a period of time and acts upon or with entities.      | Activity individuals have some temporal parts (that are not of the same type as the activity itself). An activity may include consuming, processing, transforming, modifying, relocating, using, or generating entities. |
| pink:Role            | The class of all individuals that are defined through a parthood relation to an entity. | An individual can be said to have a *role* in relation to the entity. |
| foaf:Agent           | A thing that does stuff (like person, group, software or physical artifact).            | The [FOAF] specification of a *agent* is very loose. The subclass `prov:Agent` provides further context, by saying that a `prov:agent` bears some form of responsibility for an activity, the existence of an entity or the activity of another agent. |
| pink:MaterialProcess | A process that has material as input and output. | |
| pink:Measurement     | An observation that results in a quantitative comparison of a 'property' of an 'object' with a standard reference based on a well defined mesurement procedure. | |
| pink:Computation     | A procedure that deals with quantitative symbols (i.e. symbols associated with a quantitative oriented language). | |
| pink:Material        | The class of individuals standing for an amount of matter (ordinary, anti or hybrid) substance (or mixture of substances) in different states of matter or phases. | |
| pink:Property        | A coventional semiotic sign that stands for a physical interaction with an object using an ´atomic symbol´. | A property is ´atomic´ in the sense that it is aimed to describe one and one only aspect of the object. |
| pink:Data            | Contrast from variation of properties that is encoded by an agent and that can be decoded by another agent according to a specific rule. | |
| pink:Object          | The class of all individuals whose temporal parts are of the same type as the whole. | |
| dcat:Dataset         | A collection of data, published or curated by a single agent, and available for access or download in one or more representations. | A collection of (more than one) datum, published or curated by a single agent, and available for access or download in one or more representations. |
| pink:Datum           | A self-consistent encoded data entity. | Datum are the building blocks of datasets. |
| foaf:Document        | A document. | The Document class represents those things which are, broadly conceived, 'documents'. E.g. images. |
| pink:Software        | All or part of the programs, procedures, rules, and associated documentation of an information processing system. | Software is usually used as a generic term for programs. However, in its broadest sense it can refer to all information (i.e., both programs and data) in electronic form and can provide a distinction from hardware, which refers to computers or other electronic systems on which software can exist and be used. Here we explicitly include in the definition also all the data (e.g. source code, script files) that take part in building the executable, are necessary to the execution of a program or that document it for the users. |
| dcterms:RightsStatement  | A statement about the intellectual property rights (IPR) held in or over a resource, a legal document giving official permission to do something with a resource, or a statement about access rights. | Use one of the pre-defined individuals of this class defined by EU: accr:PUBLIC, accr:NON_PUBLIC, accr:CONFIDENTIAL, accr:RESTRICTED, accr:SENSITIVE |
| dcterms:LicenseDocument  | A legal document giving official permission to do something with a resource. | |
| pink:ReliabilityDocument | | |
| prov:Agent               | An agent is something that bears some form of responsibility for an activity taking place, for the existence of an entity, or for another agent's activity. | |
| pink:Participant         | An object which is a spatial part of a process. | Example: A student during an examination. The student exists both before and after the examination. |



[FOAF]: http://xmlns.com/foaf/spec/
[PROV-O]: https://www.w3.org/TR/prov-o/

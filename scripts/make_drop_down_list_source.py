"""
This script is used to generate a csv file that can be used as the source for the drop down lists in the annotation tool. It reads the ontology and extracts the relevant classes and their labels to create a hierarchy of level 1, level 2, and level 3 classes. The resulting csv file has three columns: level1, level2, and level3, which can be used to populate the drop down lists in the annotation tool.
"""
from ontopy import get_ontology
import csv

level1 = ['Functionality Assessment', 'Safety Assessment', 'Environmental Sustainability Assessment', 'Social Sustainability Assessment', 'Economic Sustainability Assessment']

onto = get_ontology('https://w3id.org/ssbd/').load()

d = []

for l in level1:
    level2 = onto[l].subclasses()
    for k in level2:
        k_name = k.altLabel.en[0]
        level3 = list(m.altLabel.en[0]  for m in onto.get_descendants(k))
        if len(level3) > 0:
            for n in level3:
                d.append([l, k_name, n])
        else:
            d.append([l, k_name, ""])
        


with open("assessment_hierarchy.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["level1", "level2", "level3"])
    writer.writerows(d)

print("Wrote assessment_hierarchy.csv")


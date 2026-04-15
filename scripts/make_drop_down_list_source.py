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


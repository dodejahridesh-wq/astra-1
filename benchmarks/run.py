import json
from astra_core.organism import AstraOrganism

with open('benchmarks/cases.json', encoding='utf-8') as f:
    cases=json.load(f)
organism=AstraOrganism()
for case in cases:
    result=organism.run(case['goal'])
    print(case['id'], 'PASS' if result['verified'] else 'FAIL')

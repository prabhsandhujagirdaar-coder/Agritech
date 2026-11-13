import json
from collections import defaultdict

tr = json.load(open('ml/data/manifests/fruit_identifier_v2/train.json', 'r', encoding='utf-8'))
vl = json.load(open('ml/data/manifests/fruit_identifier_v2/val.json', 'r', encoding='utf-8'))
te = json.load(open('ml/data/manifests/fruit_identifier_v2/test.json', 'r', encoding='utf-8'))

m = defaultdict(set)
group_records = defaultdict(list)

for r in tr:
    key = (r['fruit_identity'], r['source_dataset'], r['group_id'])
    m[key].add('train')
    group_records[key].append(('train', r['path']))

for r in vl:
    key = (r['fruit_identity'], r['source_dataset'], r['group_id'])
    m[key].add('val')
    group_records[key].append(('val', r['path']))

for r in te:
    key = (r['fruit_identity'], r['source_dataset'], r['group_id'])
    m[key].add('test')
    group_records[key].append(('test', r['path']))

crossing = {k: list(v) for k, v in m.items() if len(v) > 1}
print(f"Total crossing groups: {len(crossing)}")
for k, sps in crossing.items():
    print(f"\nGroup: {k} -> Splits: {sps}")
    for sp, p in group_records[k][:5]:
        print(f"  [{sp}] {p}")


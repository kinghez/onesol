import json
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat()
filepath = '/home/kinghez/onesol/onesolai/products/fixtures/initial_data.json'

with open(filepath, 'r') as f:
    data = json.load(f)

for item in data:
    if item['model'] == 'products.tool':
        item['fields']['created_at'] = now
        item['fields']['updated_at'] = now

with open(filepath, 'w') as f:
    json.dump(data, f, indent=2)

print("Updated initial_data.json")

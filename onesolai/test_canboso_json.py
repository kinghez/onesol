import requests
import json

url = "https://canboso.com/api/telegram-buyer/products"
token = "tgb_d23196fded7a236498a8194e79c6b8394a6cc09723b5d756"

headers = {"App-Version": "2.0.0"}
params = {"api_key": token}

res = requests.get(url, headers=headers, params=params)
data = res.json()
print("Keys:", data.keys())
if 'products' in data:
    print("Products:", len(data['products']))
if 'data' in data:
    print("Data type:", type(data['data']))
    if isinstance(data['data'], list):
        print("Data length:", len(data['data']))
    elif isinstance(data['data'], dict):
        print("Data keys:", data['data'].keys())
print("First 200 chars of JSON:", json.dumps(data)[:200])

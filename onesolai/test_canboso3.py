import requests

url = "https://canboso.com/api/telegram-buyer/products"
token = "tgb_d23196fded7a236498a8194e79c6b8394a6cc09723b5d756"

test_cases = [
    {"desc": "Bearer + query param api_key", "headers": {"Authorization": f"Bearer {token}", "App-Version": "2.0.0"}, "params": {"api_key": token}},
    {"desc": "No Bearer + query param api_key", "headers": {"App-Version": "2.0.0"}, "params": {"api_key": token}},
    {"desc": "Bearer + custom header api_key", "headers": {"Authorization": f"Bearer {token}", "App-Version": "2.0.0", "api_key": token}, "params": {}},
    {"desc": "Bearer + custom header Api-Key", "headers": {"Authorization": f"Bearer {token}", "App-Version": "2.0.0", "Api-Key": token}, "params": {}},
    {"desc": "Bearer + custom header token", "headers": {"Authorization": f"Bearer {token}", "App-Version": "2.0.0", "token": token}, "params": {}},
]

for t in test_cases:
    res = requests.get(url, headers=t["headers"], params=t["params"])
    print(f"{t['desc']} -> {res.status_code} {res.text[:100]}")

import requests

url = "https://canboso.com/api/telegram-buyer/products"
token = "tgb_d23196fded7a236498a8194e79c6b8394a6cc09723b5d756"

headers_to_test = [
    {"App-Version": "1.0.0"},
    {"App-Version": "2.0.0"},
    {"App-Version": "3.0.0"},
    {"X-App-Version": "2.0.0"},
    {"version": "2.0.0"},
    {"User-Agent": "TelegramBot (like TwitterBot)"},
    {"User-Agent": "PostmanRuntime/7.32.3"}
]

for extra in headers_to_test:
    h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    h.update(extra)
    res = requests.get(url, headers=h)
    print(f"Testing {extra} -> {res.status_code} {res.text}")

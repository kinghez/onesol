import requests

url = "https://canboso.com/api/telegram-buyer/products"
headers = {
    "Authorization": "Bearer tgb_d23196fded7a236498a8194e79c6b8394a6cc09723b5d756",
    "Accept": "application/json"
}

print("Testing Bearer token...")
response = requests.get(url, headers=headers)
print("Status:", response.status_code)
print("Response:", response.text)

headers2 = {
    "Api-Key": "tgb_d23196fded7a236498a8194e79c6b8394a6cc09723b5d756",
    "Accept": "application/json"
}
print("\nTesting Api-Key header...")
response = requests.get(url, headers=headers2)
print("Status:", response.status_code)
print("Response:", response.text)

headers3 = {
    "X-Api-Key": "tgb_d23196fded7a236498a8194e79c6b8394a6cc09723b5d756",
    "Accept": "application/json"
}
print("\nTesting X-Api-Key header...")
response = requests.get(url, headers=headers3)
print("Status:", response.status_code)
print("Response:", response.text)


import requests

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": "Bearer test",
    "Content-Type": "application/json"
}
payload = {
    "model": "invalid-model-name",
    "messages": [{"role": "user", "content": "hi"}]
}
response = requests.post(url, headers=headers, json=payload)
print(response.status_code)
print(response.text)

import requests
import json

url = "https://canboso.com/api/v1/swagger.json"
try:
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        print("Paths:", list(data.get("paths", {}).keys()))
    else:
        print("Swagger JSON not found at v1")
except Exception as e:
    print(e)

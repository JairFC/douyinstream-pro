import requests
import uuid

url = 'https://live.douyin.com/198671092027'

cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

r = requests.get(url, headers=headers, cookies=cookies, timeout=10)

# Save HTML to file
with open('douyin_response.html', 'w', encoding='utf-8') as f:
    f.write(r.text)

print(f"HTML saved to douyin_response.html")
print(f"Length: {len(r.text)} bytes")
print(f"Status: {r.status_code}")

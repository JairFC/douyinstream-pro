import requests
import uuid

url = 'https://live.douyin.com/198671092027'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}
cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}

r = requests.get(url, headers=headers, cookies=cookies, timeout=10)

# Save to file
with open('douyin_html.txt', 'w', encoding='utf-8') as f:
    f.write(r.text)

print(f"HTML saved: {len(r.text)} bytes")

# Print first 2000 characters
print("\nFirst 2000 characters:")
print(r.text[:2000])

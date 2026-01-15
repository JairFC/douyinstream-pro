import requests

url = 'https://live.douyin.com/198671092027'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

r = requests.get(url, headers=headers, timeout=10)

# Save raw HTML
with open('douyin_raw.html', 'wb') as f:
    f.write(r.content)

# Save decoded text
with open('douyin_decoded.html', 'w', encoding='utf-8') as f:
    f.write(r.text)

print(f"Content saved")
print(f"Raw bytes: {len(r.content)}")
print(f"Decoded text: {len(r.text)} characters")
print(f"\nFirst 1000 characters:")
print(r.text[:1000])

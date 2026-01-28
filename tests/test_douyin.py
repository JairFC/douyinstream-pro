import requests
import uuid
import re
import json

# Fetch page
cookies = {'__ac_nonce': uuid.uuid4().hex[:21]}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

print("Fetching page...")
r = requests.get('https://live.douyin.com/94782239787', headers=headers, cookies=cookies, timeout=10)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

# Try pattern from Streamlink plugin
pattern = re.compile(r'self\.__pace_f\.push\(\[(\d+),"(\w+:.+?)"\]\)</script>')
matches = pattern.findall(r.text)
print(f"\nTotal __pace_f matches: {len(matches)}")

# Filter for streamStore
stream_matches = [m for m in matches if 'state' in m[1] and 'streamStore' in m[1]]
print(f"Matches with streamStore: {len(stream_matches)}")

if stream_matches:
    print("\n=== FOUND STREAM DATA ===")
    data_str = stream_matches[0][1]
    print(f"Raw data (first 300 chars): {data_str[:300]}")
    
    # Remove prefix (e.g., "d:")
    data_str = re.sub(r'^\w+:', '', data_str)
    
    # Unescape double-escaped quotes
    data_str = data_str.replace('\\"', '"')
    
    try:
        data = json.loads(data_str)
        print(f"\nJSON parsed successfully!")
        print(f"Type: {type(data)}")
        
        # Handle array wrapper format: ["$", "$L12", null, {...}]
        if isinstance(data, list) and len(data) > 3:
            print("Detected array wrapper format")
            # The actual data is usually in the last element
            for item in reversed(data):
                if isinstance(item, dict) and 'state' in item:
                    data = [item]  # Wrap in list for compatibility
                    break
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'state' in item:
                    state = item['state']
                    
                    # Check for room info
                    if 'roomStore' in state:
                        room_info = state['roomStore'].get('roomInfo', {})
                        room = room_info.get('room', {})
                        print(f"\nRoom found!")
                        print(f"  Title: {room.get('title', 'N/A')}")
                        print(f"  Status: {room.get('status', 'N/A')}")
                        print(f"  ID: {room.get('id_str', 'N/A')}")
                    
                    # Check for stream data
                    if 'streamStore' in state:
                        stream_store = state['streamStore']
                        stream_data = stream_store.get('streamData', {})
                        h264_data = stream_data.get('H264_streamData', {})
                        stream = h264_data.get('stream', {})
                        
                        if stream:
                            print(f"\nStream data found!")
                            print(f"  Qualities available: {list(stream.keys())}")
                            
                            # Get first quality URL
                            for quality_name, quality_data in stream.items():
                                if isinstance(quality_data, dict):
                                    main_data = quality_data.get('main', {})
                                    flv_url = main_data.get('flv', '')
                                    if flv_url:
                                        print(f"\n*** STREAM URL FOUND ***")
                                        print(f"  Quality: {quality_name}")
                                        print(f"  URL: {flv_url[:100]}...")
                                        break
                            break
    except Exception as e:
        print(f"\nError parsing JSON: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n✗ No stream data found in __pace_f matches")
    
    # Try alternative: RENDER_DATA
    print("\nTrying RENDER_DATA pattern...")
    render_pattern = re.compile(r'window\._ROUTER_DATA\s*=\s*({.+?})</script>')
    render_matches = render_pattern.findall(r.text)
    print(f"RENDER_DATA matches: {len(render_matches)}")

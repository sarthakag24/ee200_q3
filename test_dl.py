import urllib.request, sys
sys.stdout.reconfigure(encoding='utf-8')

fid = '12C4-teeWMDccmiihZtamcFAcRiRMqMJ4'  # Hey Jude
url = f'https://drive.google.com/uc?export=download&id={fid}'
print('Testing direct download of Hey Jude.mp3...')
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = r.read(8192)
        ct = r.headers.get('Content-Type', '')
        print(f'Got {len(data)} bytes, content-type={ct}')
        print('First 100 bytes:', data[:100])
except Exception as e:
    print(f'Error: {e}')

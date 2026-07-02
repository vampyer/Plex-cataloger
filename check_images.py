from pathlib import Path
from PIL import Image

paths = list(Path('static/images/posters').glob('*.jpg'))[:5]
for p in paths:
    print('---', p)
    data = p.read_bytes()
    print('len', len(data), 'head', data[:20])
    try:
        with Image.open(p) as img:
            print('format', img.format, 'size', img.size, 'mode', img.mode)
    except Exception as e:
        print('ERROR', e)

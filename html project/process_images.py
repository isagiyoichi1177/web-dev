from PIL import Image
from pathlib import Path

src = Path(__file__).parent / 'images' / 'IMG-20251029-WA0010.jpg'
if not src.exists():
    print('Source image not found:', src)
    raise SystemExit(1)

out_jpg = src.parent / 'IMG-20251029-WA0010_64.jpg'
out_webp = src.parent / 'IMG-20251029-WA0010_64.webp'

with Image.open(src) as im:
    # create a square crop centered
    w, h = im.size
    side = min(w, h)
    left = (w - side)//2
    top = (h - side)//2
    right = left + side
    bottom = top + side
    im_cropped = im.crop((left, top, right, bottom)).convert('RGB')
    im_resized = im_cropped.resize((64,64), Image.LANCZOS)
    im_resized.save(out_jpg, format='JPEG', quality=85)
    im_resized.save(out_webp, format='WEBP', quality=80)

print('Saved:', out_jpg.name, out_webp.name)

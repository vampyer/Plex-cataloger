#!/usr/bin/env python3
"""
Generate PNG and ICO icon assets by drawing using Pillow.

This avoids native SVG rendering dependencies so it works cross-platform.

Usage: python tools/generate_icon.py
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'icons'
OUT.mkdir(parents=True, exist_ok=True)

def rounded_rect(draw, xy, r, fill):
    x0,y0,x1,y1 = xy
    draw.rectangle([x0+r, y0, x1-r, y1], fill=fill)
    draw.rectangle([x0, y0+r, x1, y1-r], fill=fill)
    draw.pieslice([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=fill)
    draw.pieslice([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=fill)
    draw.pieslice([x0, y1-2*r, x0+2*r, y1], 90, 180, fill=fill)
    draw.pieslice([x1-2*r, y1-2*r, x1, y1], 0, 90, fill=fill)

def draw_icon(size):
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    # background rounded rect (dark)
    bg_color = (15,23,36,255)
    rounded_rect(draw, (0,0,size,size), r=int(size*0.14), fill=bg_color)

    # inner white panel
    box_margin = int(size*0.14)
    left = box_margin
    top = box_margin
    right = size - box_margin
    bottom = size - box_margin
    rounded_rect(draw, (left, top, right, bottom), r=int(size*0.08), fill=(255,255,255,255))

    # draw wordmark 'pleX' centered: 'ple' black, 'X' gold
    try:
        # try common bundled font
        font_path = None
        import pkgutil, os
        # Pillow ships DejaVuSans; try to locate it
        try:
            from PIL import ImageFont
            font_path = ImageFont.truetype('DejaVuSans-Bold.ttf', 10).path
        except Exception:
            font_path = None
        if font_path:
            font_size = max(12, int(size * 0.36))
            font = ImageFont.truetype(font_path, font_size)
        else:
            from PIL import ImageFont
            font = ImageFont.load_default()
    except Exception:
        from PIL import ImageFont
        font = ImageFont.load_default()

    text = 'pleX'
    # measure text using textbbox
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
    except Exception:
        # fallback to font.getsize
        try:
            w, h = font.getsize(text)
        except Exception:
            w, h = (int(size*0.6), int(size*0.3))

    cx = size // 2
    cy = size // 2
    x = cx - w // 2
    y = cy - h // 2 - int(size*0.03)

    # draw 'ple' and 'X' separately so we can color them differently
    try:
        bbox_ple = draw.textbbox((0,0), 'ple', font=font)
        w_ple = bbox_ple[2] - bbox_ple[0]
    except Exception:
        try:
            w_ple, _ = font.getsize('ple')
        except Exception:
            w_ple = int(w * 0.75)

    draw.text((x, y), 'ple', font=font, fill=(0,0,0,255))
    draw.text((x + w_ple, y), 'X', font=font, fill=(255,203,47,255))

    return img

sizes = [16, 24, 32, 48, 64, 128, 256]
png_paths = []
for s in sizes:
    img = draw_icon(s)
    out_png = OUT / f'icon_{s}.png'
    img.save(out_png, format='PNG')
    png_paths.append(out_png)

# Build ICO
from PIL import Image
images = [Image.open(p).convert('RGBA') for p in png_paths]
ico_path = OUT / 'plex_cataloger.ico'
images_sorted = sorted(images, key=lambda im: im.width, reverse=True)
images_sorted[0].save(ico_path, format='ICO', sizes=[(im.width, im.height) for im in images_sorted])

print('Icons written to', OUT)

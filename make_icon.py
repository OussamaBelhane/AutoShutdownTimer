import os
from PIL import Image, ImageDraw

def generate():
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    frames = []
    
    for w, h in sizes:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        
        pad = int(w * 0.05)
        d.ellipse([pad, pad, w - pad, h - pad], fill=(18, 20, 24, 255), outline=(88, 166, 255, 255), width=max(1, int(w * 0.04)))
        
        cx, cy = w // 2, h // 2
        rad = int(w * 0.28)
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], start=300, end=240, fill=(0, 210, 255, 255), width=max(2, int(w * 0.07)))
        
        lw = max(2, int(w * 0.07))
        d.line([cx, cy - rad - int(w * 0.04), cx, cy], fill=(248, 81, 73, 255), width=lw)
        
        frames.append(img)
    
    folder = os.path.dirname(os.path.abspath(__file__))
    frames[0].save(os.path.join(folder, "app_icon.png"))
    frames[0].save(os.path.join(folder, "app_icon.ico"), format="ICO", sizes=sizes)

if __name__ == "__main__":
    generate()

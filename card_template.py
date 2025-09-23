# card_template.py
from PIL import Image, ImageDraw, ImageFont
import io

def make_image_card(buyer: str, amount, txhash: str) -> io.BytesIO:
    img = Image.new('RGB', (600, 200), color=(25, 25, 112))
    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()
    draw.text((20, 30), f"FomoFrog Purchase Verified 🐸", fill="white", font=font)
    draw.text((20, 70), f"Buyer: {buyer}", fill="white", font=font)
    draw.text((20, 100), f"Amount: {amount}", fill="white", font=font)
    draw.text((20, 130), f"Tx: {txhash}", fill="white", font=font)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

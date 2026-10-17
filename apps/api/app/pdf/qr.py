"""QR codes embedded as data URIs, so the PDF needs no external files."""

import base64
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from qrcode.image.pil import PilImage


def qr_data_uri(url: str) -> str:
    code = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=6, border=1)
    code.add_data(url)
    code.make(fit=True)
    buffer = io.BytesIO()
    code.make_image(image_factory=PilImage, fill_color="black", back_color="white").save(
        buffer, format="PNG"
    )
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

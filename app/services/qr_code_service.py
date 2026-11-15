from io import BytesIO

import qrcode


class QRCodeService:
    def make_png(self, absolute_url):
        qr = qrcode.QRCode(box_size=8, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(absolute_url)
        qr.make(fit=True)
        stream = BytesIO()
        qr.make_image(fill_color='black', back_color='white').save(stream, format='PNG')
        return stream.getvalue()

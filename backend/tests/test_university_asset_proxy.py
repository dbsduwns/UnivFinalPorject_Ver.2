import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from app.routers.notice import proxy_notice_image, proxy_university_pdf


class UniversityAssetProxyTest(unittest.TestCase):
    url = "https://web.kangnam.ac.kr/comm/cmnFile/download.do?id=example"

    def response(self, payload, content_type="application/octet-stream"):
        response = Mock(ok=True, is_redirect=False, is_permanent_redirect=False)
        response.headers = {"content-type": content_type}
        response.iter_content.return_value = [payload]
        return response

    @patch("app.routers.notice.university_get")
    def test_pdf_and_image_bytes(self, get):
        for handler, payload, media in [
            (proxy_university_pdf, b"%PDF-1.7\n", "application/pdf"),
            (proxy_notice_image, b"\x89PNG\r\n\x1a\n", "image/png"),
        ]:
            upstream = self.response(payload)
            get.return_value = upstream
            result = handler(self.url)
            self.assertEqual(result.body, payload)
            self.assertEqual(result.media_type, media)
            upstream.close.assert_called()

    @patch("app.routers.notice.university_get")
    def test_login_html_is_not_a_pdf(self, get):
        get.return_value = self.response(b"<html>login</html>")
        with self.assertRaises(HTTPException) as error:
            proxy_university_pdf(self.url)
        self.assertEqual(error.exception.status_code, 415)

    @patch("app.routers.notice.university_get")
    def test_external_redirect_is_rejected(self, get):
        upstream = self.response(b"")
        upstream.is_redirect = True
        upstream.headers = {"location": "https://example.com/file.pdf"}
        get.return_value = upstream
        with self.assertRaises(HTTPException) as error:
            proxy_university_pdf(self.url)
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(get.call_count, 1)

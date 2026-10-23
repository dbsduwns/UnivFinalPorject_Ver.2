"""Verified TLS for the university server's incomplete intermediate chain."""
import ssl
from pathlib import Path

import certifi
import requests
from requests.adapters import HTTPAdapter


class UniversityTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl.create_default_context(cafile=certifi.where())
        context.load_verify_locations(
            cafile=str(Path(__file__).with_name("certs") / "rapidssl-tls-rsa-ca-g1.pem")
        )
        # The intermediate must still chain to a trusted root.
        context.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
        kwargs["ssl_context"] = context
        super().init_poolmanager(*args, **kwargs)


def university_get(url: str, **kwargs):
    with requests.Session() as session:
        session.mount("https://web.kangnam.ac.kr/", UniversityTLSAdapter())
        return session.get(url, **kwargs)

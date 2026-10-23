# University TLS chain

`rapidssl-tls-rsa-ca-g1.pem` is the public RapidSSL TLS RSA CA G1
intermediate, issued by DigiCert Global Root G2. Retrieved from
https://cacerts.digicert.com/RapidSSLTLSRSACAG1.crt with HTTPS verification.

The university server omits this intermediate. `university_http.py` adds it
to the normal certifi trust store only for https://web.kangnam.ac.kr/.
Hostname, expiry, signature and trusted-root validation remain enabled;
partial-chain trust is disabled. No private keys are included.

Ship this PEM with the backend (the existing Docker COPY includes it).
If the university changes issuers, update this intermediate from the CA's
authenticated distribution endpoint and verify a live university request.
The mobile app must access university images/PDFs through the API proxy.

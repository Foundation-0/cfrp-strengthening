.PHONY: verify verify-fast verify-track-1-flexure certificates

verify: verify-fast verify-track-1-flexure

verify-fast:
	python3 -m unittest discover -s tests -v
	python3 src/flexure440.py tracks/track-1/input.json > /dev/null

verify-track-1-flexure:
	python3 results/track-1-flexure/verify.py

certificates:
	python3 results/track-1-flexure/verify.py --write
	cp results/track-1-flexure/certificate.json certificates/track-1-flexure.json
	cd certificates && sha256sum track-1-flexure.json > SHA256SUMS
	sha256sum src/flexure440.py tracks/track-1/input.json tracks/track-1/expected.json results/track-1-flexure/certificate.json > commitment/SHA256SUMS
	sha256sum commitment/SHA256SUMS | awk '{print $$1}' > commitment/ROOT

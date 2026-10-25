export OPENBLAS_NUM_THREADS := 1
export OMP_NUM_THREADS := 1

.PHONY: verify verify-fast verify-track-1-flexure verify-hashes certificates

verify: verify-fast verify-track-1-flexure verify-hashes

# The checker run is piped to a JSON parse, not gated on its exit code:
# a beam that fails a check exits 1 by design, and the tests assert the
# outcomes. The check lines stay visible on stderr when something fails.
verify-fast:
	python3 -m unittest discover -s tests -v
	python3 src/flexure440.py tracks/track-1/input.json | python3 -c "import json, sys; json.load(sys.stdin)"

verify-track-1-flexure:
	python3 results/track-1-flexure/verify.py

verify-hashes:
	diff results/track-1-flexure/certificate.json certificates/track-1-flexure.json
	cd certificates && sha256sum -c SHA256SUMS
	sha256sum -c commitment/SHA256SUMS
	test "$$(sha256sum commitment/SHA256SUMS | awk '{print $$1}')" = "$$(cat commitment/ROOT)"

certificates:
	python3 results/track-1-flexure/verify.py --write
	cp results/track-1-flexure/certificate.json certificates/track-1-flexure.json
	cd certificates && sha256sum track-1-flexure.json > SHA256SUMS
	sha256sum src/flexure440.py tracks/track-1/input.json tracks/track-1/expected.json results/track-1-flexure/certificate.json > commitment/SHA256SUMS
	sha256sum commitment/SHA256SUMS | awk '{print $$1}' > commitment/ROOT

export OPENBLAS_NUM_THREADS := 1
export OMP_NUM_THREADS := 1

.PHONY: verify verify-fast verify-track-1-flexure verify-hashes certificates

verify: verify-fast verify-track-1-flexure verify-hashes

# The checker run is gated on its exit code and on its JSON.
# A beam that fails a check exits 1 by design, so exit 0 and exit 1
# pass when the output is valid JSON with no NaN or Infinity value.
# Exit 2, a crash, invalid JSON, or a NaN or Infinity value fails.
# The check lines stay visible on stderr when something fails.
verify-fast:
	python3 -m unittest discover -s tests -v
	python3 -c "import json, subprocess, sys; p = subprocess.run([sys.executable, 'src/flexure440.py', 'tracks/track-1/input.json'], stdout=subprocess.PIPE, text=True); sys.stdout.write(p.stdout); json.loads(p.stdout, parse_constant=lambda c: (_ for _ in ()).throw(ValueError('invalid JSON constant: ' + c))); sys.exit(0 if p.returncode in (0, 1) else 1)"

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

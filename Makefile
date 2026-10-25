verify:
	python3 -m unittest discover -s tests -v
	python3 src/flexure440.py tracks/track-1/input.json > /dev/null

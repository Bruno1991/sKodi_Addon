.PHONY: bootstrap validate test manifest build clean tree

bootstrap:
	python tools/bootstrap_artwork.py

validate:
	python tools/validate_addons.py
	python tools/secret_scan.py
	python -m compileall -q addons tools tests

test:
	python -m unittest discover -s tests -p "test_*.py" -v

manifest:
	python tools/generate_structure_manifest.py

build: bootstrap validate test
	python tools/build_repo.py
	python tools/generate_structure_manifest.py

clean:
	python tools/clean_build.py

tree:
	python tools/print_tree.py

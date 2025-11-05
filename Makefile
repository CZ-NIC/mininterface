MANIFEST := pyproject.toml
TAG := $(shell grep "^version" $(MANIFEST) | pz --search '"(\d+\.\d+\.\d+(?:-(?:rc|alpha|beta)\.?\d+)?)?"')

.PHONY: release validate pre-check readme
default: release

validate:
	@echo "Validating pyproject extras..."
	@extra/validate_dependencies.py || (echo "Validation failed. Aborting." && exit 1)

release: validate
	@echo "Tagging release $(TAG)"
	git tag $(TAG)
	git push origin $(TAG)
	@echo "Deploying documentation..."
	mkdocs gh-deploy

pre-check:
	pre-commit uninstall && \
	pre-commit install && \
	pre-commit autoupdate && \
	pre-commit install --hook-type commit-msg -f

readme:
	@echo "Generating README.md from docs/index.md..."
	python3 extra/convert_readme.py
	@echo "README.md successfully generated!"
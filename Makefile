MANIFEST := pyproject.toml
TAG := $(shell grep "^version" $(MANIFEST) | pz --search '"(\d+\.\d+\.\d+(?:-(?:rc|alpha|beta)\d+)?)?"')

.PHONY: release validate
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

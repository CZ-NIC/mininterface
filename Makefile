MANIFEST := pyproject.toml
TAG := $(shell grep "^version" $(MANIFEST) | pz --search '"(\d+\.\d+\.\d+(?:-(?:rc|alpha|beta)\.?\d+)?)?"')
README_PATH := asset/readme-readonly.md

.PHONY: release validate pre-check readme
default: release

validate:
	@echo "Validating pyproject extras..."
	@extra/validate_dependencies.py || (echo "Validation failed. Aborting." && exit 1)

release: readme-with-commit validate
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

readme-with-commit: readme
	@if git diff --quiet $(README_PATH); then \
		echo "No changes detected in $(README_PATH)"; \
	else \
		echo "Changes detected. Committing..."; \
		git add $(README_PATH); \
		git commit -m "docs: readme"; \
	fi

readme:
	@echo "Generating asset/readme-readonly.md from docs/index.md..."
	@python3 extra/convert_readme.py || (echo "README generation failed. Aborting." && exit 1)
export TAG := `grep version pyproject.toml | pz --search '"(\d+\.\d+\.\d+(?:rc\d+)?)?"'`

release:
	git tag $(TAG)
	git push origin $(TAG)
	mkdocs gh-deploy

pre-check:
	pre-commit uninstall && \
	pre-commit install && \
	pre-commit autoupdate && \
	pre-commit install --hook-type commit-msg -f

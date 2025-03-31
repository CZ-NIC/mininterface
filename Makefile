export TAG := `grep "^version" pyproject.toml | pz --search '"(\d+\.\d+\.\d+(?:-(?:rc|alpha|beta)\d+)?)?"'`

release:
	git tag $(TAG)
	git push origin $(TAG)
	mkdocs gh-deploy
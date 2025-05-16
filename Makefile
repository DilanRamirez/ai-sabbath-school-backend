# Makefile

# Run backend unit tests
test:
	pytest tests --maxfail=1 --disable-warnings -q

# Format backend using black
format:
	black .

# Check formatting (used in GHA)
check-format:
	black --check .

# Run the GitHub Actions workflow locally
test-gha:
	act -j backend-tests -W .github/workflows/backend.yml --container-architecture linux/amd64

# Full local CI simulation
ci:
	make format
	make check-format
	make test

# Build or rebuild the semantic FAISS index for lessons + books
index:
	PYTHONPATH=python python app/indexing/index_builder.py

.PHONY: serve-local
serve-local:
	python -m uvicorn app.main:app \
		--reload \
		--host 0.0.0.0 \
		--port 8001

# DOCKER COMMANDS
up:
	docker compose up --build
down:
	docker compose down
reload:
	docker compose down && docker compose up --build
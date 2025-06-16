# Makefile

# RUN GITHUB ACTIONS LOCALLY
run-gha:
	act
	
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
	python3 -m uvicorn app.main:app \
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

# Run the backend image locally with environment variables
run-image:
	docker run --rm \
		-p 8001:8001 \
		--name ss-backend-test \
		--env-file .env \
		ai-sabbath-school-backend:dev

# Azure Container Registry (ACR) Deployment Configuration
IMAGE_NAME=ai-sabbath-school-backend
RESOURCE_GROUP=ai-sabbath-school
REGISTRY_NAME=aisabbathschool
AZURE_ENVIRONMENT_NAME=ai-sabbath-school-env
HUB=$(REGISTRY_NAME).azurecr.io
FULL_IMAGE_NAME=$(HUB)/$(IMAGE_NAME):latest

# Login to Azure CLI
login-azure:
	az login

# Login to Azure Container Registry (ACR)
login-acr:
	az acr login --name $(REGISTRY_NAME)

# Build Docker image for production (linux/amd64 platform)
build:
	docker build --platform linux/amd64 \
		-t $(IMAGE_NAME) .

# Build Docker image for dev (macOS/arm64 platform)
build-dev:
	docker build --platform linux/arm64/v8 \
		-t $(IMAGE_NAME):dev .

# Tag image for ACR
tag:
	docker tag $(IMAGE_NAME) $(FULL_IMAGE_NAME)

# Push the image to ACR
push:
	make login-acr
	make build
	make tag
	docker push $(FULL_IMAGE_NAME)

# Deploy to Azure Container Apps
create:
	az containerapp create \
		--name $(IMAGE_NAME) \
		--resource-group $(RESOURCE_GROUP) \
		--environment $(AZURE_ENVIRONMENT_NAME) \
		--image $(FULL_IMAGE_NAME) \
		--target-port 8001 \
		--ingress 'external' \
		--registry-login-server $(HUB) \
		--registry-username $${AZURE_REGISTRY_USERNAME} \
		--registry-password $${AZURE_REGISTRY_PASSWORD}

# Full pipeline: build, tag, push
deploy: push

# Update existing Azure Container App with the latest image
update: push
	az containerapp update \
		--name $(IMAGE_NAME) \
		--resource-group $(RESOURCE_GROUP) \
		--image $(FULL_IMAGE_NAME) \
		--min-replicas 1
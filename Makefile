COMPOSE_FILE ?= docker-compose.clara.yml
REMOVE_ORPHANS ?=
IMAGE ?= ghcr.io/adb-xkc85723/janus-base:latest

ifndef GHCR_KEY
ifeq ($(filter build push,$(MAKECMDGOALS)),)
else
$(error GHCR_KEY is required. Usage: make build GHCR_KEY=/path/to/ssh/key)
endif
endif

.PHONY: build push up down

build:
	@set -e; eval "$$(./configure.sh $(GHCR_KEY))"; docker buildx build --ssh default=$$SSH_AUTH_SOCK -f Dockerfile -t $(IMAGE) .

push: build
	docker push $(IMAGE)

up:
	docker compose -f $(COMPOSE_FILE) up --build

down:
	docker compose -f $(COMPOSE_FILE) down --volumes $(REMOVE_ORPHANS)

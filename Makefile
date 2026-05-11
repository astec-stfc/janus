COMPOSE_FILE ?= docker-compose.clara.yml
REMOVE_ORPHANS ?=
IMAGE ?= ghcr.io/adb-xkc85723/janus-base:latest

ifndef GITLAB_KEY
ifeq ($(filter build push,$(MAKECMDGOALS)),)
else
$(error GITLAB_KEY is required. Usage: make build GITLAB_KEY=/path/to/ssh/key)
endif
endif

.PHONY: build push up down

build:
	@set -e; eval "$$(./configure.sh $(GITLAB_KEY))"; docker buildx build --ssh default=$$SSH_AUTH_SOCK -f Dockerfile -t $(IMAGE) .

push: build
	docker push $(IMAGE)

up:
	docker compose -f $(COMPOSE_FILE) up --build

down:
	docker compose -f $(COMPOSE_FILE) down --volumes $(REMOVE_ORPHANS)
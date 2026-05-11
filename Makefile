COMPOSE_FILE ?= docker-compose.clara.yml
REMOVE_ORPHANS ?= ""

.PHONY: build push up down

build:
ifndef GITLAB_KEY
 $(error GITLAB_KEY is required for build. Usage: make build GITLAB_KEY=/path/to/ssh/key)
endif
 eval "$$(./configure.sh $(GITLAB_KEY))" && \
 docker buildx build --ssh default=$$SSH_AUTH_SOCK -f Dockerfile -t ghcr.io/adb-xkc85723/janus-base:latest .

push: build
 docker push ghcr.io/adb-xkc85723/janus-base:latest

up:
 docker compose -f $(COMPOSE_FILE) up --build

down:
 docker compose -f $(COMPOSE_FILE) down --volumes $(REMOVE_ORPHANS)
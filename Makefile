

FACILITY=clara
MODE ?= stack

IMAGE ?= ghcr.io/adb-xkc85723/janus-base:latest
REMOVE_ORPHANS ?=

# Default values
COMPOSE_FILE =
ENV_FILE =
CLIENT =

# Mode selection
ifeq ($(MODE),server)
COMPOSE_FILE := docker-compose.server.yml
ENV_FILE := .env.server
CLIENT := janus-server
endif

ifeq ($(MODE),client)
COMPOSE_FILE := docker-compose.client.$(FACILITY).yml
ENV_FILE := .env.client
CLIENT := $(shell grep CLIENT_ID $(ENV_FILE) | cut -d '=' -f2)
endif

ifeq ($(MODE),prod)
COMPOSE_FILE := docker-compose.client.prod.yml
ENV_FILE := .env.prod
CLIENT := $(shell grep CLIENT_ID $(ENV_FILE) | cut -d '=' -f2)
endif

ifeq ($(MODE),stack)
COMPOSE_FILE := docker-compose.$(FACILITY).yml
ENV_FILE := .env.stack
CLIENT := $(shell grep CLIENT_ID $(ENV_FILE) | cut -d '=' -f2)
endif


ifndef GHCR_KEY
ifeq ($(filter build push,$(MAKECMDGOALS)),)
else
$(error GHCR_KEY is required. Usage: make build GHCR_KEY=/path/to/ssh/key)
endif
endif

.PHONY: build push up down server client prod stack

build:
	@set -e; eval "$$(./configure.sh $(GHCR_KEY))"; docker buildx build --ssh default=$$SSH_AUTH_SOCK -f Dockerfile -t $(IMAGE) .

push: build
	docker push $(IMAGE)

client-up:
	$(MAKE) up MODE=client

server-up:
	$(MAKE) up MODE=server

stack-up:
	$(MAKE) up MODE=stack

prod-up:
	$(MAKE) up MODE=prod

client-down:
	$(MAKE) down MODE=client

server-down:
	$(MAKE) down MODE=server

stack-down:
	$(MAKE) down MODE=stack

prod-down:
	$(MAKE) down MODE=prod

up:
	docker compose $(if $(CLIENT),-p $(CLIENT)) \
	$(if $(ENV_FILE),--env-file $(ENV_FILE)) \
	-f $(COMPOSE_FILE) up --build

down:
	docker compose $(if $(CLIENT),-p $(CLIENT)) \
	$(if $(ENV_FILE),--env-file $(ENV_FILE)) \
	-f $(COMPOSE_FILE) down --volumes $(REMOVE_ORPHANS)
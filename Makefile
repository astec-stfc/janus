COMPOSE_FILE ?= docker-compose.clara.yml
FACILITY ?= CLARA
REMOVE_ORPHANS ?=
IMAGE ?= ghcr.io/adb-xkc85723/janus-base:latest

TARGET_FACILITY := $(firstword $(filter clara isis,$(MAKECMDGOALS)))
ifeq ($(TARGET_FACILITY),clara)
FACILITY := CLARA
COMPOSE_FILE := docker-compose.clara.yml
endif
ifeq ($(TARGET_FACILITY),isis)
FACILITY := ISIS
COMPOSE_FILE := docker-compose.isis.yml
endif

ifndef GHCR_KEY
ifeq ($(filter build push,$(MAKECMDGOALS)),)
else
$(error GHCR_KEY is required. Usage: make build GHCR_KEY=/path/to/ssh/key)
endif
endif

.PHONY: build push up down clara isis

build:
	@set -e; eval "$$(./configure.sh $(GHCR_KEY))"; docker buildx build --ssh default=$$SSH_AUTH_SOCK -f Dockerfile -t $(IMAGE) .

push: build
	docker push $(IMAGE)

up:
	FACILITY=$(FACILITY) docker compose -f $(COMPOSE_FILE) up --build

down:
	FACILITY=$(FACILITY) docker compose -f $(COMPOSE_FILE) down --volumes $(REMOVE_ORPHANS)

clara:
	@:

isis:
	@:

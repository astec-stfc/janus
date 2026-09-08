#!/usr/bin/env bash
#
# ISIS deployment entry point: build every Janus image using the same compose
# files as 'make stack-up', retag them into the ISIS Docker registry and push,
# so the stack can be deployed from Portainer with the
# docker-compose.portainer.yml alongside this script.
#
# "isis" here is the deployment site (the ISIS registry and Portainer host),
# not the accelerator: the stack deployed there runs the JFEL facility, which
# is what docker-compose.portainer.yml expects. Hence the jfel default below;
# pass -f <facility> to override.
#
# Builds go through 'docker compose build' rather than a hand-maintained list
# of 'docker build' calls. Contexts, build args, --ssh and the repo/version
# pins in .versions.env therefore stay in step with the dev stack on their
# own: whatever 'make stack-up FACILITY=<f>' builds is what gets pushed.
#
# The dev compose files bind-mount ./janus_common into most containers at
# runtime. Portainer stacks have no checkout of this repo, so every image that
# mounts it gets janus_common baked in as an extra layer after the build. The
# mount targets are read from the resolved compose config, not hardcoded.
#
# The frontend gets one further layer: vite.config.ts is re-copied in from a
# staging dir on local disk, then the image is verified before anything is
# pushed. See patch_frontend below for why that is not paranoia.
#
# Usage:
#   ./deploy/isis/build-and-push.sh -k /path/to/ssh/key [options]
#
# Options:
#   -k, --key PATH        SSH key for private repo access during builds,
#                         set up via configure.sh (same key as
#                         'make build GHCR_KEY=...'). Not needed if you have
#                         already run 'source ./configure.sh /path/to/key'.
#   -r, --registry HOST   Target registry (default: svc-docker-registry.controls.isis.rl.ac.uk)
#   -t, --tag TAG         Image tag (default: latest)
#   -f, --facility NAME   Facility, lowercase (default: jfel)
#   -a, --allowed-hosts H Comma-separated hostnames the frontend dev server
#                         accepts, or "all" (default: athena.isis.rl.ac.uk)
#       --no-cache        Build without the layer cache
#       --no-push         Build and tag only, skip the push
#   -h, --help            Show this help
#
# Lattice/SimFrame repos and version pins are NOT options: they come from
# .versions.env, exactly as they do for 'make stack-up'. Edit that file to
# change them. Note that astec-stfc/laura-lattices contains only JFEL, so
# building any other facility needs the internal GitLab lattice repo there.
#
# All options can also be set via environment variables:
#   REGISTRY, TAG, FACILITY, GHCR_KEY, ALLOWED_HOSTS

set -euo pipefail

REGISTRY="${REGISTRY:-svc-docker-registry.controls.isis.rl.ac.uk}"
TAG="${TAG:-latest}"
FACILITY="${FACILITY:-jfel}"
GHCR_KEY="${GHCR_KEY:-}"
ALLOWED_HOSTS="${ALLOWED_HOSTS:-athena.isis.rl.ac.uk}"
PUSH=1
NO_CACHE=()

# Print the header comment block above as help, so the two cannot drift.
usage() { awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        -k|--key)           GHCR_KEY="$2"; shift 2 ;;
        -r|--registry)      REGISTRY="$2"; shift 2 ;;
        -t|--tag)           TAG="$2"; shift 2 ;;
        -f|--facility)      FACILITY="$2"; shift 2 ;;
        -a|--allowed-hosts) ALLOWED_HOSTS="$2"; shift 2 ;;
        --no-cache)         NO_CACHE=(--no-cache); shift ;;
        --no-push)          PUSH=0; shift ;;
        -h|--help)          usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# Docker treats a registry without a dot or port as a Docker Hub namespace
# (docker.io/<name>/...), silently pushing to the wrong place.
case "$REGISTRY" in
    *.*|*:*) ;;
    *)
        echo "Error: registry '$REGISTRY' has no dot or port, so Docker would treat it" >&2
        echo "as a docker.io namespace. Use the FQDN or host:port form, e.g." >&2
        echo "  REGISTRY=$REGISTRY.example.ac.uk or REGISTRY=$REGISTRY:5000" >&2
        exit 1
        ;;
esac

FACILITY="$(echo "$FACILITY" | tr '[:upper:]' '[:lower:]')"

COMPOSE_FILE="docker-compose.$FACILITY.yml"
ENV_FILE=".env.stack"

for f in "$COMPOSE_FILE" "$ENV_FILE" .versions.env; do
    if [ ! -f "$f" ]; then
        echo "Error: $f not found (facility '$FACILITY')" >&2
        exit 1
    fi
done

export DOCKER_BUILDKIT=1

# Several images clone private repos during build and need an SSH key,
# set up via configure.sh exactly like 'make build'.
if [ -n "$GHCR_KEY" ]; then
    if [ ! -f "$GHCR_KEY" ]; then
        echo "Error: SSH key file not found: $GHCR_KEY" >&2
        exit 1
    fi
    eval "$(./configure.sh "$GHCR_KEY")"
elif ! ssh-add -l >/dev/null 2>&1; then
    echo "Error: no SSH agent with a loaded key found." >&2
    echo "Either run 'source ./configure.sh /path/to/ssh/key' first," >&2
    echo "or pass the key with -k /path/to/ssh/key (or GHCR_KEY=...)." >&2
    exit 1
fi

# Stale __pycache__ dirs in janus_common (root-owned when created by a
# container through a bind mount) break the build context transfer; they are
# regenerated on demand, so drop them. Falls back to a root container for
# dirs the current user cannot remove.
if ! find janus_common -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null \
   || [ -n "$(find janus_common -name __pycache__ 2>/dev/null)" ]; then
    docker run --rm -v "$ROOT/janus_common:/jc" alpine \
        sh -c 'find /jc -depth -name __pycache__ -exec rm -rf {} +'
fi

# The Makefile exports these on top of --env-file so that ${VAR} in the
# compose files resolves the same way here as it does for 'make up'.
set -a
# shellcheck disable=SC1091
. ./.versions.env
set +a

PROJECT="$(grep '^CLIENT_ID' "$ENV_FILE" | cut -d '=' -f2)"
PROJECT="${PROJECT:-janus-stack}"

compose() {
    docker compose -p "$PROJECT" \
        --env-file "$ENV_FILE" --env-file .versions.env \
        -f "$COMPOSE_FILE" "$@"
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "==> Resolving compose config ($COMPOSE_FILE, project $PROJECT)"
compose config --format json > "$WORKDIR/config.json"

# Turn the resolved config into (a) a compose override that names every built
# image after the registry, and (b) a manifest of what to bake and push.
FACILITY="$FACILITY" ALLOWED_HOSTS="$ALLOWED_HOSTS" REGISTRY="$REGISTRY" TAG="$TAG" \
python3 - "$WORKDIR" <<'PY'
import json, os, sys

workdir = sys.argv[1]
facility = os.environ["FACILITY"]
registry, tag = os.environ["REGISTRY"], os.environ["TAG"]
allowed_hosts = os.environ["ALLOWED_HOSTS"]

# Registry image names use hyphens; the two facility-scoped services carry the
# facility as a suffix, matching docker-compose.portainer.yml.
def image_name(service):
    special = {"ioc": f"ioc-{facility}",
               "epics_to_lattice": f"epics-to-lattice-{facility}"}
    return special.get(service, service.replace("_", "-"))

config = json.load(open(f"{workdir}/config.json"))
override, manifest = {"services": {}}, []

for name, svc in sorted(config.get("services", {}).items()):
    if "build" not in svc:
        continue                      # third-party image (broker, lattice_db)
    image = f"{registry}/janus/{image_name(name)}:{tag}"
    entry = {"image": image}
    if name == "frontend":
        # ALLOWED_HOSTS is a build arg on the frontend only; the dev compose
        # files have no reason to set it, so it is injected here.
        entry["build"] = {"args": {"ALLOWED_HOSTS": allowed_hosts}}
    override["services"][name] = entry

    dest = ""
    for vol in svc.get("volumes", []):
        if "janus_common" in str(vol.get("source", "")):
            dest = vol.get("target", "")
            break
    context = svc.get("build", {}).get("context", "")
    manifest.append(f"{name}\t{image}\t{dest}\t{context}")

json.dump(override, open(f"{workdir}/override.yml", "w"), indent=2)
open(f"{workdir}/manifest.tsv", "w").write("\n".join(manifest) + "\n")
print(f"    {len(manifest)} buildable services, "
      f"{sum(1 for m in manifest if m.rsplit(chr(9), 1)[1])} with janus_common")
PY

# Force vite.config.ts into the frontend image and prove it is usable.
#
# Vite starts with no config at all if the file is absent, which leaves
# server.allowedHosts empty and makes every request from a non-localhost name
# (athena.isis.rl.ac.uk) return 403 Blocked request. The file has gone missing
# from a built image before without the build failing: a broken node_modules
# entry under apps/web/frontend made BuildKit's concurrent context walk
# silently drop it and two other files, so the image built, pushed and
# deployed looking healthy and only 403'd in a browser.
#
# So re-copy the config from a staging dir on local disk, immune to whatever
# the source filesystem is doing, then check the result. A failure here aborts
# the run, so a bad frontend image is never pushed.
patch_frontend() {
    local image="$1" context="$2" stage="$WORKDIR/vite"

    if [ -z "$context" ] || [ ! -f "$context/vite.config.ts" ]; then
        echo "Error: vite.config.ts not found in frontend build context: ${context:-<unset>}" >&2
        exit 1
    fi

    echo "==> Ensuring vite.config.ts in frontend (allowed hosts: $ALLOWED_HOSTS)"
    mkdir -p "$stage"
    cp "$context/vite.config.ts" "$stage/vite.config.ts"
    docker build -q -t "$image" -f - "$stage" >/dev/null <<DOCKERFILE
FROM $image
COPY vite.config.ts /app/vite.config.ts
DOCKERFILE

    if ! docker run --rm --entrypoint sh "$image" -c '
        test -f /app/vite.config.ts     || { echo "  /app/vite.config.ts missing"; exit 1; }
        grep -q allowedHosts /app/vite.config.ts \
                                        || { echo "  allowedHosts not in vite.config.ts"; exit 1; }
        test -n "$ALLOWED_HOSTS"        || { echo "  ALLOWED_HOSTS not set in image"; exit 1; }
    '; then
        echo "Error: frontend image failed verification; not pushing." >&2
        exit 1
    fi
}

echo ""
echo "==> Building via docker compose"
compose -f "$WORKDIR/override.yml" build "${NO_CACHE[@]+"${NO_CACHE[@]}"}"

IMAGES=()
while IFS=$'\t' read -r service image dest context; do
    [ -n "$service" ] || continue
    if [ -n "$dest" ]; then
        echo "==> Baking janus_common into $service at $dest"
        docker build -q -t "$image" -f - janus_common >/dev/null <<DOCKERFILE
FROM $image
COPY . $dest
DOCKERFILE
    fi
    if [ "$service" = "frontend" ]; then
        patch_frontend "$image" "$context"
    fi
    IMAGES+=("$image")
done < "$WORKDIR/manifest.tsv"

echo ""
if [ "$PUSH" = "1" ]; then
    for image in "${IMAGES[@]}"; do
        echo "==> Pushing $image"
        docker push "$image"
    done
else
    echo "Skipping push (--no-push). Built images:"
    printf '  %s\n' "${IMAGES[@]}"
fi

echo ""
echo "Done. ${#IMAGES[@]} images for registry $REGISTRY (tag: $TAG, facility: $FACILITY)."

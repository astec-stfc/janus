FROM ghcr.io/adb-xkc85723/janus-simcodes:latest

ARG SIMBA_REPO=https://github.com/astec-stfc/simba.git
ARG SIMBA_VERSION=v0.4.0
ARG LAURA_REPO=https://github.com/astec-stfc/laura.git
ARG LAURA_VERSION=v1.0.0
ARG LAURA_LATTICE_REPO=https://github.com/astec-stfc/laura-lattices.git
ARG LAURA_LATTICES_VERSION=v0.1.0
ARG ACRONICTA_CATAP_REPO=https://github.com/astec-stfc/acronicta-catap.git
ARG ACRONICTA_CATAP_VERSION=v0.1.0

ADD API /home/web/webapp

RUN mkdir -p /home/web/webapp/Output/CLARA && \
    mkdir -p /home/web/webapp/Output/ISIS && \
    mkdir -p /home/web/webapp/Output/JFEL && \
    chmod -R a+rwX /home/web/webapp/Output/CLARA && \
    chmod -R a+rwX /home/web/webapp/Output/ISIS && \
    chmod -R a+rwX /home/web/webapp/Output/JFEL

WORKDIR /laura
# different checkout behaviour for tags vs branches, so check if the tag exists first
RUN git fetch --all --tags && \
    if git rev-parse --verify "refs/tags/${LAURA_VERSION}" >/dev/null 2>&1; then \
        git checkout --detach "${LAURA_VERSION}"; \
    else \
        git checkout --detach "origin/${LAURA_VERSION}"; \
    fi

WORKDIR /simba
# different checkout behaviour for tags vs branches, so check if the tag exists first
RUN git fetch --all --tags && \
    if git rev-parse --verify "refs/tags/${SIMBA_VERSION}" >/dev/null 2>&1; then \
        git checkout --detach "${SIMBA_VERSION}"; \
    else \
        git checkout --detach "origin/${SIMBA_VERSION}"; \
    fi

RUN --mount=type=ssh,required=false bash -lc '\
set -e; \
for repo in "${LAURA_LATTICE_REPO}"; do \
  case "$repo" in \
    git@*|ssh://*) \
      mkdir -p /root/.ssh; \
      ssh-keyscan gitlab.stfc.ac.uk >> /root/.ssh/known_hosts 2>/dev/null || true; \
      ;; \
    http://*|https://*) \
      ;; \
    *) \
      echo "Unsupported repo format: $repo" >&2; \
      exit 1; \
      ;; \
  esac; \
done; \
case "${LAURA_LATTICE_REPO}" in \
  http://*|https://*) \
    git clone --branch "${LAURA_LATTICES_VERSION:-main}" "${LAURA_LATTICE_REPO}" /laura-lattices; \
    ;; \
  git@*|ssh://*) \
    git clone --branch "${LAURA_LATTICES_VERSION:-main}" "${LAURA_LATTICE_REPO}" /laura-lattices; \
    ;; \
  *) \
    echo "Unsupported LAURA_LATTICE_REPO format: ${LAURA_LATTICE_REPO}" >&2; \
    exit 1; \
    ;; \
esac; \
'

WORKDIR /home/web/webapp
ENV PYTHONPATH=/home/web/webapp
ENV PYTHONUNBUFFERED=1

ADD entrypoint.sh /home/web/webapp/
ADD requirements.txt /home/web/webapp/
RUN pip install -r requirements.txt

ENTRYPOINT ["./entrypoint.sh"]
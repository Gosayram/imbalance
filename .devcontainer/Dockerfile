FROM python:3.14-slim

ARG TARGETARCH
ARG GIT_CLIFF_VERSION=2.13.1

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	UV_LINK_MODE=copy

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		ca-certificates \
		curl \
		git \
		make \
		sqlite3 \
	&& rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN case "${TARGETARCH}" in \
		"amd64") GIT_CLIFF_ARCH="x86_64" ;; \
		"arm64") GIT_CLIFF_ARCH="aarch64" ;; \
		*) echo "Unsupported architecture for git-cliff: ${TARGETARCH}" >&2; exit 1 ;; \
	esac \
	&& curl -fsSL \
		"https://github.com/orhun/git-cliff/releases/download/v${GIT_CLIFF_VERSION}/git-cliff-${GIT_CLIFF_VERSION}-${GIT_CLIFF_ARCH}-unknown-linux-gnu.tar.gz" \
		-o /tmp/git-cliff.tar.gz \
	&& tar -xzf /tmp/git-cliff.tar.gz -C /tmp \
	&& install "/tmp/git-cliff-${GIT_CLIFF_VERSION}/git-cliff" /usr/local/bin/git-cliff \
	&& rm -rf /tmp/git-cliff*

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspaces/imbalance

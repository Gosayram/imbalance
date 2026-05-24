FROM python@sha256:c845af9399020c7e562969a13689e929074a10fd057acd1b1fad06a2fb068e97 # 3.14-slim

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

RUN groupadd -g 1000 app && useradd -m -u 1000 -g app app

ENV PATH="/home/app/.local/bin:$PATH" \
	HOME="/home/app"

RUN mkdir -p /workspaces/imbalance && chown -R app:app /workspaces

USER app
WORKDIR /workspaces/imbalance

FROM mcr.microsoft.com/devcontainers/base:debian

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client azure-cli \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx

# Fix SSL cert path: Python's openssl looks in /.dockerless/ssl/certs which
# doesn't exist at runtime. Symlink it to the real system cert directory.
RUN mkdir -p /.dockerless/ssl && ln -s /etc/ssl/certs /.dockerless/ssl/certs

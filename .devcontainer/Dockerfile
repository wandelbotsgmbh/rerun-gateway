FROM mcr.microsoft.com/devcontainers/base:debian

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client azure-cli \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx

# Fix SSL: uv's standalone Python expects /etc/ssl/cert.pem (Alpine/macOS path)
# but Debian puts the CA bundle at /etc/ssl/certs/ca-certificates.crt.
RUN ln -sf /etc/ssl/certs/ca-certificates.crt /etc/ssl/cert.pem
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

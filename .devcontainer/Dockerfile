FROM mcr.microsoft.com/devcontainers/base:bullseye

RUN apt-get update && apt install -y --no-install-recommends \
  python3-pip \
  shellcheck \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install \
  poetry \
  pre-commit \
  detect-secrets

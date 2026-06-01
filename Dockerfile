# md2pdf in a box: the CLI + headless Chromium + CJK fonts, ready to run.
#
#   docker run --rm -v "$PWD:/work" ghcr.io/suyw-0123/md-to-pdf-cli report.md
#
# The current directory is mounted at /work, so the PDF lands next to the input.
FROM python:3.12-slim

# - PLAYWRIGHT_BROWSERS_PATH: install Chromium to a fixed, world-readable path so
#   it works no matter which UID the container is run as (`--user $(id -u)`).
# - MD2PDF_AUTO_INSTALL_BROWSER=0: the browser is baked in at build time; never
#   try to download it at runtime.
# - MD2PDF_CHROMIUM_NO_SANDBOX=1: Chromium can't use its sandbox inside a typical
#   container, so launch with --no-sandbox --disable-dev-shm-usage.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
    MD2PDF_AUTO_INSTALL_BROWSER=0 \
    MD2PDF_CHROMIUM_NO_SANDBOX=1 \
    HOME=/tmp

# CJK + emoji fonts so Chinese/Japanese/Korean text renders instead of tofu.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        fonts-noto-cjk fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install the CLI, then Chromium together with its system libraries. The browser
# goes to PLAYWRIGHT_BROWSERS_PATH; world-readable so any UID can launch it.
RUN pip install . \
    && playwright install --with-deps chromium \
    && chmod -R a+rX /opt/playwright

# Convert out of a mounted working directory.
WORKDIR /work
ENTRYPOINT ["md2pdf"]

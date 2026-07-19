FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --wheel-dir /wheels .

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DIVINE_CONFIG_DIR=/home/divine/.config/divine-router \
    DIVINE_DATA_DIR=/home/divine/.local/share/divine-router \
    DIVINE_LOG_DIR=/home/divine/.local/state/divine-router/log

RUN groupadd --system divine && useradd --system --gid divine --create-home divine
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

USER divine
WORKDIR /home/divine
EXPOSE 8742
VOLUME ["/home/divine/.config/divine-router", "/home/divine/.local/share/divine-router"]

CMD ["divine", "serve"]

# syntax=docker/dockerfile:1
# HuellaIP IPFIX collector: GoFlow2 v2.2.7 plus the supervisor in colector/.
# Build natively on each architecture: the goflow2 -v check runs the target binary.

ARG GOFLOW2_VERSION=2.2.7
# Set by BuildKit for the platform being built (amd64 or arm64).
ARG TARGETARCH

# GoFlow2 static release binaries, pinned by SHA-256 per architecture.
FROM scratch AS goflow2-amd64
ARG GOFLOW2_VERSION
ADD --checksum=sha256:63d3bb6c4e458f56ae3268eac74979da1fee0cea5342362295e7d587784af14b --chmod=755 \
    https://github.com/netsampler/goflow2/releases/download/v${GOFLOW2_VERSION}/goflow2-${GOFLOW2_VERSION}-linux-amd64 /goflow2

FROM scratch AS goflow2-arm64
ARG GOFLOW2_VERSION
ADD --checksum=sha256:cf7dfdb63b6df54a5b7c5b274f275d036a046d6e998036f7beb832377937571c --chmod=755 \
    https://github.com/netsampler/goflow2/releases/download/v${GOFLOW2_VERSION}/goflow2-${GOFLOW2_VERSION}-linux-arm64 /goflow2

FROM goflow2-${TARGETARCH} AS goflow2

FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170

LABEL org.opencontainers.image.source="https://github.com/huellaip/huellaip" \
      org.opencontainers.image.description="HuellaIP IPFIX collector: GoFlow2 plus a supervisor that writes hourly JSON files" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="0.1.2"

COPY --from=goflow2 /goflow2 /usr/local/bin/goflow2
RUN /usr/local/bin/goflow2 -v

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin colector \
    && mkdir -p /datos/flujos \
    && chown -R 10001:10001 /datos

COPY mapping.yaml /etc/colector/mapping.yaml
COPY colector /opt/colector/colector

ENV PYTHONPATH=/opt/colector \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 10001
VOLUME /datos
EXPOSE 2055/udp
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-m", "colector.health"]
ENTRYPOINT ["python", "-m", "colector"]

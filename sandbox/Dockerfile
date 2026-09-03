# OmiAgent sandbox runtime image — the only place the agent executes code.
# Build:  docker build -t omiagent/runtime:local sandbox/
FROM node:20-bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv git ripgrep curl jq less procps \
 && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir --break-system-packages pytest
WORKDIR /workspace
CMD ["sleep", "infinity"]

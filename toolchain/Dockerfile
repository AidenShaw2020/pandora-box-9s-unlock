# Compatibility compiler for the observed glibc 2.25 ARMv7 firmware.
# This old userspace is a build tool, not a network service.
FROM arm32v7/debian:stretch-slim
RUN printf 'deb [check-valid-until=no] http://archive.debian.org/debian stretch main\n' > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update -qq \
    && apt-get install -y -qq --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

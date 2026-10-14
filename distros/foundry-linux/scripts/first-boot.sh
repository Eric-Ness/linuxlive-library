#!/bin/sh
# Once, on a computer Foundry was installed on, before its first login screen:
# let containers (podman, distrobox) start on demand, and note when it was set up.
set -eu
systemctl enable --now podman.socket
mkdir -p /var/lib/foundry
date -u +%Y-%m-%dT%H:%M:%SZ >/var/lib/foundry/installed

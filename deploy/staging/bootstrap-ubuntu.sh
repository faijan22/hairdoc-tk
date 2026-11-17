#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this one-time bootstrap with sudo." >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID}" != "ubuntu" ]]; then
  echo "This bootstrap supports Ubuntu Server only." >&2
  exit 1
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  systemctl enable --now docker
  echo "Docker Engine and Compose v2 are already installed; leaving them unchanged."
  exit 0
fi

CONFLICTS=()
for package in docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc; do
  if dpkg-query -W -f='${Status}' "${package}" 2>/dev/null | grep -q "install ok installed"; then
    CONFLICTS+=("${package}")
  fi
done
if (( ${#CONFLICTS[@]} )); then
  echo "Conflicting container packages are installed: ${CONFLICTS[*]}" >&2
  echo "Review existing server workloads before replacing them with Docker's official packages." >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat >/etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

DEPLOY_USER="${SUDO_USER:-}"
if [[ -n "${DEPLOY_USER}" && "${DEPLOY_USER}" != "root" ]]; then
  usermod -aG docker "${DEPLOY_USER}"
  echo "Docker installed. Log out and back in once so ${DEPLOY_USER} can use Docker."
else
  echo "Docker installed. Add the intended deploy user to the docker group before continuing."
fi

echo "Do not enable UFW until SSH, TCP 80 and TCP/UDP 443 are explicitly allowed."


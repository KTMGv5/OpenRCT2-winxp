#!/usr/bin/env bash
#
# setup-jenkins-host.sh - Turnkey Jenkins and toolchain installer for Ubuntu 24.04 LTS (pvelocal)
#
# Run with root/sudo privileges:
#   sudo ./ci/scripts/setup-jenkins-host.sh
#

set -euo pipefail

echo "=========================================================="
echo " Setting up Jenkins & OpenRCT2-winxp Build Environment   "
echo " Target: Ubuntu 24.04 LTS (Noble)                       "
echo "=========================================================="

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)." >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "1. Installing base dependencies and Java 21 LTS..."
apt-get update -qq
apt-get install -y -qq \
    curl \
    wget \
    gnupg \
    software-properties-common \
    fontconfig \
    openjdk-21-jre-headless \
    git \
    patch \
    bzip2 \
    pkgconf \
    cmake \
    meson \
    ninja-build \
    python3 \
    zip \
    unzip

echo "2. Installing MinGW-w64 toolchain (GCC 13+)..."
apt-get install -y -qq \
    build-essential \
    mingw-w64 \
    gcc-mingw-w64-i686 \
    g++-mingw-w64-i686 \
    binutils-mingw-w64-i686

echo "3. Configuring POSIX threading model for MinGW-w64..."
update-alternatives --set i686-w64-mingw32-gcc /usr/bin/i686-w64-mingw32-gcc-posix 2>/dev/null || true
update-alternatives --set i686-w64-mingw32-g++ /usr/bin/i686-w64-mingw32-g++-posix 2>/dev/null || true

echo "4. Adding official Jenkins LTS repository..."
mkdir -p /etc/apt/keyrings
wget -qO /etc/apt/keyrings/jenkins-keyring.asc https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key
echo "deb [signed-by=/etc/apt/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" > /etc/apt/sources.list.d/jenkins.list

apt-get update -qq
echo "Installing Jenkins..."
apt-get install -y -qq jenkins

echo "5. Starting and enabling Jenkins systemd service..."
systemctl daemon-reload
systemctl enable --now jenkins

# Wait for Jenkins to start up and generate initialAdminPassword
echo "Waiting for Jenkins to initialize (up to 30 seconds)..."
for i in {1..30}; do
    if [ -f /var/lib/jenkins/secrets/initialAdminPassword ]; then
        break
    fi
    sleep 1
done

# Allow firewall port 8080 if firewalld or ufw is active
if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    echo "Allowing port 8080 in firewalld..."
    firewall-cmd --permanent --add-port=8080/tcp || true
    firewall-cmd --reload || true
elif command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    echo "Allowing port 8080 in ufw..."
    ufw allow 8080/tcp || true
fi

# Ensure jenkins user has permission to read build cache if present
if [ -d "/home/tyler/OpenRCT2-XP" ]; then
    echo "Granting jenkins user read permissions to /home/tyler/OpenRCT2-XP..."
    chmod 755 /home/tyler || true
    chmod -R a+rX /home/tyler/OpenRCT2-XP/build || true
fi

echo ""
echo "=========================================================="
echo " Jenkins installation complete!                           "
echo " Web UI: http://$(hostname -I | awk '{print $1}'):8080   "
echo " Initial Admin Password:                                  "
if [ -f /var/lib/jenkins/secrets/initialAdminPassword ]; then
    cat /var/lib/jenkins/secrets/initialAdminPassword
else
    echo " (Check: /var/lib/jenkins/secrets/initialAdminPassword)"
fi
echo "=========================================================="

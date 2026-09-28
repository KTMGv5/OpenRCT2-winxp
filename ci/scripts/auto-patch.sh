#!/usr/bin/env bash
#
# auto-patch.sh - Automated patch verification and upstream update checker for OpenRCT2-winxp
#
# Usage:
#   ./ci/scripts/auto-patch.sh [TAG_OR_BRANCH] [BASE_PATCH]
#
# Example:
#   ./ci/scripts/auto-patch.sh v0.5.5
#   ./ci/scripts/auto-patch.sh v0.5.6 xp-compat-v0.5.5.patch
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UPSTREAM_REPO="https://github.com/OpenRCT2/OpenRCT2.git"

TARGET_TAG="${1:-}"
BASE_PATCH="${2:-}"

# If no target tag provided, query upstream for the latest release tag
if [ -z "${TARGET_TAG}" ]; then
    echo "Querying upstream releases from ${UPSTREAM_REPO}..."
    LATEST_TAG=$(git ls-remote --tags --refs --sort='v:refname' "${UPSTREAM_REPO}" 'v*' | tail -n 1 | sed 's|.*refs/tags/||')
    if [ -z "${LATEST_TAG}" ]; then
        echo "Error: Could not determine latest upstream tag." >&2
        exit 1
    fi
    TARGET_TAG="${LATEST_TAG}"
    echo "Found latest upstream release: ${TARGET_TAG}"
fi

# Locate base patch to test
if [ -z "${BASE_PATCH}" ]; then
    if [ -f "${ROOT_DIR}/xp-compat-${TARGET_TAG}.patch" ]; then
        BASE_PATCH="${ROOT_DIR}/xp-compat-${TARGET_TAG}.patch"
    elif [ -f "${ROOT_DIR}/xp-compat-v0.5.5.patch" ]; then
        BASE_PATCH="${ROOT_DIR}/xp-compat-v0.5.5.patch"
    elif [ -f "${ROOT_DIR}/xp-compat.patch" ]; then
        BASE_PATCH="${ROOT_DIR}/xp-compat.patch"
    else
        echo "Error: No base patch file found." >&2
        exit 1
    fi
fi

if [[ "${BASE_PATCH}" != /* ]]; then
    BASE_PATCH="${ROOT_DIR}/${BASE_PATCH}"
fi

echo "=================================================="
echo " Upstream Target: ${TARGET_TAG}"
echo " Base Patch:      $(basename "${BASE_PATCH}")"
echo "=================================================="

WORK_DIR="$(mktemp -d -t openrct2-patch-XXXXXX)"
cleanup() {
    rm -rf "${WORK_DIR}"
}
trap cleanup EXIT

echo "Cloning upstream OpenRCT2 (${TARGET_TAG})..."
git clone --depth 1 --branch "${TARGET_TAG}" "${UPSTREAM_REPO}" "${WORK_DIR}/OpenRCT2"

echo "Testing patch application (dry-run)..."
cd "${WORK_DIR}/OpenRCT2"

if patch -p1 --dry-run < "${BASE_PATCH}"; then
    echo ""
    echo "=================================================="
    echo "[SUCCESS] Patch applies cleanly to ${TARGET_TAG}!"
    echo "=================================================="
    
    NEW_PATCH="${ROOT_DIR}/xp-compat-${TARGET_TAG}.patch"
    if [ ! -f "${NEW_PATCH}" ] && [ "${BASE_PATCH}" != "${NEW_PATCH}" ]; then
        echo "Creating copy for target version: $(basename "${NEW_PATCH}")"
        cp "${BASE_PATCH}" "${NEW_PATCH}"
    fi
    exit 0
else
    echo ""
    echo "=================================================="
    echo "[CONFLICT] Patch does not apply cleanly to ${TARGET_TAG}."
    echo "Attempting 3-way or reject generation for review..."
    echo "=================================================="
    
    patch -f -p1 < "${BASE_PATCH}" || true
    echo ""
    echo "Files with conflicts / rejections:"
    find . -name "*.rej" -print
    exit 1
fi

# OpenRCT2 Windows XP Jenkins CI/CD Setup

This directory contains the automation, scripts, and configuration for running Jenkins builds and patch management for OpenRCT2 on Windows XP.

## Server Information
- **Host**: `pvelocal.home.local` (`192.168.1.113`)
- **OS**: Ubuntu 24.04.5 LTS (Noble Numbat)
- **Port**: `http://pvelocal.home.local:8080` (or `http://192.168.1.113:8080`)

---

## Quick Setup on Ubuntu Server (`pvelocal`)

Run the automated installer script:
```bash
sudo ./ci/scripts/setup-jenkins-host.sh
```

This will automatically:
1. Install Java 21 LTS (`openjdk-21-jre-headless`)
2. Configure official Jenkins LTS repository and install Jenkins
3. Install MinGW-w64 toolchain (GCC 13+) and configure POSIX threading model
4. Start Jenkins as a systemd service (`jenkins.service`)
5. Open firewall port `8080/tcp` (if `ufw` is active)
6. Output the initial administrator password

---

## Configuring the Pipeline in Jenkins UI

1. Open **`http://pvelocal.home.local:8080`** in your browser.
2. Enter the Administrator password shown at the end of setup (or run `sudo cat /var/lib/jenkins/secrets/initialAdminPassword`).
3. Select **Install suggested plugins** (Git, Pipeline, etc.).
4. Create your admin user account.
5. In Jenkins Dashboard:
   - Click **New Item** -> Name it `OpenRCT2-winxp` -> Select **Pipeline** -> Click **OK**.
   - Under **Build Triggers**, optionally enable **GitHub hook trigger for GITScm polling** or **Poll SCM**.
   - Under **Pipeline**:
     - Definition: **Pipeline script from SCM**
     - SCM: **Git**
     - Repository URL: `https://github.com/KTMGv5/OpenRCT2-winxp.git` (or your local git path `/home/tyler/OpenRCT2-XP/.git`)
     - Branch Specifier: `*/master`
     - Script Path: `Jenkinsfile`
   - Click **Save**.

---

## Pipeline Features

When you click **Build with Parameters** in Jenkins, the following options are available:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OPENRCT2_VERSION` | `v0.5.5` | Upstream OpenRCT2 git tag or release to build |
| `PATCH_FILE` | *(auto-detected)* | Specific patch file (defaults to `xp-compat-${OPENRCT2_VERSION}.patch`) |
| `BUILD_TYPE` | `Release` | CMake build mode (`Release` or `Debug`) |
| `CLEAN_BUILD` | `false` | Clean working tree before compilation |
| `REUSE_BUILD_CACHE` | `true` | Reuse precompiled static libraries to accelerate builds from ~30m to ~2m |

### Pipeline Stages
1. **Toolchain Check**: Validates GCC 13+ MinGW posix compiler, CMake, Meson, Ninja, Python 3.
2. **Workspace & Cache Setup**: Mounts or copies prebuilt third-party dependencies.
3. **Determine & Verify Patch**: Validates that the Windows XP compatibility patch applies cleanly to upstream source code before building.
4. **Build Dependencies & OpenRCT2**: Multi-threaded parallel compilation (`-j$(nproc)`).
5. **Windows XP Compatibility Verification**: Runs `check_xp_compat.py` on the output binaries to verify 0 Vista+ API or DLL imports.
6. **Package Release**: Creates `OpenRCT2-winxp-${VERSION}.zip`.
7. **Artifact Archival**: Publishes the `.zip` archive and standalone binaries as downloadable artifacts directly on the Jenkins build page.

---

## Automated Patch Checking (`auto-patch.sh`)

To test if current XP compatibility patches work with new upstream releases:

```bash
# Check against the latest upstream release tag:
./ci/scripts/auto-patch.sh

# Or check against a specific upstream version:
./ci/scripts/auto-patch.sh v0.5.6 xp-compat-v0.5.5.patch

# Or check against upstream develop branch:
./ci/scripts/auto-patch.sh develop
```

If the patch applies cleanly, it automatically creates `xp-compat-<VERSION>.patch`. If upstream changes broke compatibility, it reports rejected hunks (`.rej`) for targeted patching.

---

## Nightly Development Pipeline (`Jenkinsfile.nightly`)

The `OpenRCT2-winxp-nightly` pipeline automates builds from upstream `develop`:
- **Schedule**: Automatically triggers daily at `02:00 AM` (`H 2 * * *`).
- **Dynamic Artifacts**: Creates `OpenRCT2-winxp-nightly-<YYYYMMDD>-<SHORT_SHA>.zip`.
- **Pre-Flight Validation**: Executes `auto-patch.sh develop` and `check_xp_compat.py` to prevent broken builds.
- **Log & Artifact Retention**: Automatically retains the latest 10 builds and 5 release archives.

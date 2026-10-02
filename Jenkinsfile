pipeline {
    agent any

    parameters {
        string(
            name: 'OPENRCT2_REPO',
            defaultValue: 'https://github.com/KTMGv5/OpenRCT2-WindowsXP.git',
            description: 'Git repository URL of OpenRCT2 (defaults to our native Windows XP fork)'
        )
        string(
            name: 'OPENRCT2_BRANCH',
            defaultValue: 'winxp',
            description: 'Git tag or branch of OpenRCT2 to build (e.g. winxp, develop, v0.5.5)'
        )
        string(
            name: 'PATCH_FILE',
            defaultValue: '',
            description: 'Optional path of patch file (leave empty when building native OpenRCT2-WindowsXP fork)'
        )
        choice(
            name: 'BUILD_TYPE',
            choices: ['Release', 'Debug'],
            description: 'CMake build type'
        )
        booleanParam(
            name: 'CLEAN_BUILD',
            defaultValue: false,
            description: 'Clean working tree before building (warning: rebuilding all dependencies takes 20-30 min)'
        )
        booleanParam(
            name: 'REUSE_BUILD_CACHE',
            defaultValue: true,
            description: 'Reuse precompiled dependency libraries from /home/tyler/OpenRCT2-XP/build if available'
        )
        booleanParam(
            name: 'PUBLISH_TO_GITHUB',
            defaultValue: true,
            description: 'Automatically publish the release zip and binaries to GitHub Releases'
        )
        string(
            name: 'GITHUB_REPO',
            defaultValue: 'KTMGv5/OpenRCT2-WindowsXP',
            description: 'Target GitHub repository to post releases to (owner/repo)'
        )
    }

    environment {
        OPENRCT2_REPO_URL = "${params.OPENRCT2_REPO ?: 'https://github.com/KTMGv5/OpenRCT2-WindowsXP.git'}"
        OPENRCT2_BRANCH   = "${params.OPENRCT2_BRANCH ?: (params.OPENRCT2_VERSION ?: 'winxp')}"
        BUILD_TYPE        = "${params.BUILD_TYPE ?: 'Release'}"
        GITHUB_REPO       = "${params.GITHUB_REPO ?: 'KTMGv5/OpenRCT2-WindowsXP'}"
        NUM_CORES         = sh(script: 'nproc 2>/dev/null || echo 4', returnStdout: true).trim()
        BUILD_DATE        = sh(script: 'date +%Y%m%d', returnStdout: true).trim()
    }

    stages {
        stage('Toolchain Check') {
            steps {
                echo "=== Verifying Build Toolchain ==="
                sh '''
                    echo "Checking compiler..."
                    i686-w64-mingw32-gcc --version | head -n 1
                    i686-w64-mingw32-g++ --version | head -n 1

                    echo "Checking build utilities..."
                    cmake --version | head -n 1
                    meson --version
                    ninja --version
                    python3 --version
                    which patch wget pkgconf
                '''
            }
        }

        stage('Prepare Workspace & Cache') {
            steps {
                script {
                    if (params.CLEAN_BUILD) {
                        echo "Performing clean build..."
                        sh 'make clean || true'
                    }

                    // Check for precompiled libraries cache to accelerate build times
                    sh '''
                        if [ "${REUSE_BUILD_CACHE}" = "true" ] && [ ! -d "build" ]; then
                            if [ -d "/home/tyler/OpenRCT2-XP/build" ]; then
                                echo "Populating dependency cache from /home/tyler/OpenRCT2-XP/build..."
                                cp -r /home/tyler/OpenRCT2-XP/build .
                                [ -f "/home/tyler/OpenRCT2-XP/i686-w64-mingw32-pkg-config" ] && cp /home/tyler/OpenRCT2-XP/i686-w64-mingw32-pkg-config .
                                echo "Cache copied successfully."
                            fi
                        fi
                    '''
                }
            }
        }

        stage('Determine & Verify Source') {
            steps {
                script {
                    def patch = params.PATCH_FILE.trim()
                    if (patch) {
                        env.RESOLVED_PATCH = "${WORKSPACE}/${patch}"
                        echo "Using specified patch file: ${env.RESOLVED_PATCH}"
                        sh "make test-patch OPENRCT2_REPO=${OPENRCT2_REPO_URL} OPENRCT2_BRANCH=${OPENRCT2_BRANCH} PATCH_FILE=\"${env.RESOLVED_PATCH}\""
                    } else if (OPENRCT2_REPO_URL.contains("OpenRCT2-WindowsXP") || OPENRCT2_BRANCH == "winxp") {
                        echo "Building from native Windows XP fork (${OPENRCT2_REPO_URL} @ ${OPENRCT2_BRANCH}) — no patch required."
                        env.RESOLVED_PATCH = ""
                    } else {
                        if (fileExists("xp-compat-${OPENRCT2_BRANCH}.patch")) {
                            patch = "xp-compat-${OPENRCT2_BRANCH}.patch"
                        } else if (fileExists("xp-compat.patch")) {
                            patch = "xp-compat.patch"
                        } else {
                            error("Building upstream without native XP changes, but no suitable patch found for ${OPENRCT2_BRANCH}!")
                        }
                        env.RESOLVED_PATCH = "${WORKSPACE}/${patch}"
                        echo "Testing patch application against ${OPENRCT2_BRANCH}..."
                        sh "make test-patch OPENRCT2_REPO=${OPENRCT2_REPO_URL} OPENRCT2_BRANCH=${OPENRCT2_BRANCH} PATCH_FILE=\"${env.RESOLVED_PATCH}\""
                    }
                    sh """
                        if [ -d "OpenRCT2/.git" ]; then
                            git -C OpenRCT2 reset --hard HEAD
                            git -C OpenRCT2 clean -fd
                            git -C OpenRCT2 remote set-url origin ${OPENRCT2_REPO_URL}
                            git -C OpenRCT2 fetch origin ${OPENRCT2_BRANCH}
                            git -C OpenRCT2 checkout -B ${OPENRCT2_BRANCH} FETCH_HEAD
                        else
                            git clone --depth 1 --branch ${OPENRCT2_BRANCH} ${OPENRCT2_REPO_URL} OpenRCT2
                        fi
                        rm -rf OpenRCT2/_build OpenRCT2/built OpenRCT2/configured
                    """
                }
            }
        }

        stage('Build Dependencies & OpenRCT2') {
            steps {
                echo "Compiling OpenRCT2 (${OPENRCT2_BRANCH}) from ${OPENRCT2_REPO_URL} with ${NUM_CORES} parallel jobs..."
                sh """
                    make all \
                        OPENRCT2_REPO="${OPENRCT2_REPO_URL}" \
                        OPENRCT2_BRANCH="${OPENRCT2_BRANCH}" \
                        OPENRCT2_VERSION="${OPENRCT2_BRANCH}" \
                        PATCH_FILE="${env.RESOLVED_PATCH}" \
                        CMAKE_BUILD_TYPE=${BUILD_TYPE} \
                        CPU_CORES=${NUM_CORES}
                """
            }
        }

        stage('Windows XP Compatibility Verification') {
            steps {
                echo "Scanning generated PE binaries for Windows Vista/7/8/10+ API violations..."
                sh """
                    make check \
                        OPENRCT2_REPO="${OPENRCT2_REPO_URL}" \
                        OPENRCT2_BRANCH="${OPENRCT2_BRANCH}" \
                        OPENRCT2_VERSION="${OPENRCT2_BRANCH}" \
                        PATCH_FILE="${env.RESOLVED_PATCH}"
                """
            }
        }

        stage('Package Release') {
            steps {
                echo "Packaging portable Windows XP release zip..."
                sh """
                    make package \
                        OPENRCT2_REPO="${OPENRCT2_REPO_URL}" \
                        OPENRCT2_BRANCH="${OPENRCT2_BRANCH}" \
                        OPENRCT2_VERSION="${OPENRCT2_BRANCH}" \
                        PATCH_FILE="${env.RESOLVED_PATCH}"
                """
                echo "Verifying mandatory TLS certificate store (cacert.pem)..."
                sh '''
                    ZIP_FILE=$(ls OpenRCT2-*-windows-portable-win32.zip 2>/dev/null | head -n 1)
                    if [ -z "${ZIP_FILE}" ]; then
                        echo "Error: No release package found." >&2
                        exit 1
                    fi
                    echo "Checking package: ${ZIP_FILE}"
                    if unzip -l "${ZIP_FILE}" | grep -q "cacert.pem"; then
                        echo "[PASS] cacert.pem verified inside release package!"
                    else
                        echo "[FAIL] FATAL ERROR: cacert.pem is missing from the package!" >&2
                        exit 1
                    fi
                '''
            }
        }

        stage('Publish to GitHub') {
            when {
                expression { return params.PUBLISH_TO_GITHUB != false }
            }
            steps {
                script {
                    echo "Preparing GitHub Release on ${GITHUB_REPO}..."
                    try {
                        withCredentials([string(credentialsId: 'github-token', variable: 'GH_TOKEN')]) {
                            sh '''
                                SHORT_SHA=$(git -C OpenRCT2 rev-parse --short HEAD 2>/dev/null || echo "${OPENRCT2_BRANCH}")
                                ZIP_FILE=$(ls OpenRCT2-*-windows-portable-win32.zip 2>/dev/null | head -n 1)
                                if [ -z "${ZIP_FILE}" ]; then
                                    echo "Error: No release zip found." >&2
                                    exit 1
                                fi

                                if echo "${OPENRCT2_BRANCH}" | grep -q "^v0\\."; then
                                    TAG="${OPENRCT2_BRANCH}"
                                    TITLE="OpenRCT2 ${TAG} - Windows XP Edition"
                                    PRERELEASE_OPT=""
                                    echo "Publishing stable release: ${TAG}"
                                else
                                    TAG="develop"
                                    TITLE="OpenRCT2 develop (${SHORT_SHA}) - Windows XP Edition"
                                    PRERELEASE_OPT="--prerelease"
                                    echo "Publishing pre-release: ${TAG} (${SHORT_SHA})"
                                    gh release delete "${TAG}" -y --cleanup-tag --repo "${GITHUB_REPO}" 2>/dev/null || true
                                fi

                                echo "Publishing release artifact: ${ZIP_FILE} to ${GITHUB_REPO} (${TAG})"

                                if gh release view "${TAG}" --repo "${GITHUB_REPO}" >/dev/null 2>&1; then
                                    echo "Updating existing GitHub release ${TAG}..."
                                    gh release upload "${TAG}" "${ZIP_FILE}" OpenRCT2/_build/openrct2.exe OpenRCT2/_build/openrct2-cli.exe --repo "${GITHUB_REPO}" --clobber
                                else
                                    echo "Creating new GitHub release for ${TAG}..."
                                    gh release create "${TAG}" "${ZIP_FILE}" OpenRCT2/_build/openrct2.exe OpenRCT2/_build/openrct2-cli.exe \
                                        --repo "${GITHUB_REPO}" \
                                        --title "${TITLE}" \
                                        --notes "Native build of OpenRCT2 Windows XP Edition from commit ${SHORT_SHA}. Built natively for Windows XP (NT 5.1) without binary patching. Includes modern TLS 1.2/1.3 multiplayer networking, root CA certificate store (cacert.pem), and legacy graphics driver fallbacks." \
                                        ${PRERELEASE_OPT}
                                fi
                                echo "GitHub release published successfully to https://github.com/${GITHUB_REPO}/releases !"
                            '''
                        }
                    } catch (Exception e) {
                        echo "Notice: Could not publish to GitHub: ${e.getMessage()}"
                        echo "To enable GitHub Release uploading: In Jenkins -> Manage Jenkins -> Credentials -> add a 'Secret text' with ID 'github-token' containing your GitHub Personal Access Token."
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Build, XP compatibility check, and packaging passed successfully!"
            archiveArtifacts artifacts: 'OpenRCT2-*-windows-portable-win32.zip, OpenRCT2/_build/openrct2.exe, OpenRCT2/_build/openrct2-cli.exe', fingerprint: true, allowEmptyArchive: true
        }
        failure {
            echo "Build or compatibility check failed. Please inspect console logs."
        }
    }
}

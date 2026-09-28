pipeline {
    agent any

    parameters {
        string(
            name: 'OPENRCT2_VERSION',
            defaultValue: 'v0.5.5',
            description: 'Git tag or branch of OpenRCT2 to build (e.g. v0.5.5, v0.4.32)'
        )
        string(
            name: 'PATCH_FILE',
            defaultValue: '',
            description: 'Optional path or filename of patch (defaults to xp-compat-${OPENRCT2_VERSION}.patch)'
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
    }

    environment {
        OPENRCT2_VER = "${params.OPENRCT2_VERSION}"
        BUILD_TYPE   = "${params.BUILD_TYPE}"
        NUM_CORES    = sh(script: 'nproc 2>/dev/null || echo 4', returnStdout: true).trim()
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

        stage('Determine & Verify Patch') {
            steps {
                script {
                    def patch = params.PATCH_FILE.trim()
                    if (!patch) {
                        if (fileExists("xp-compat-${OPENRCT2_VER}.patch")) {
                            patch = "xp-compat-${OPENRCT2_VER}.patch"
                        } else if (fileExists("xp-compat.patch")) {
                            patch = "xp-compat.patch"
                        } else {
                            error("No suitable patch found for OpenRCT2 ${OPENRCT2_VER}!")
                        }
                    }
                    echo "Using patch file: ${patch}"
                    env.RESOLVED_PATCH = patch

                    echo "Testing patch application against upstream ${OPENRCT2_VER}..."
                    sh "make test-patch OPENRCT2_VERSION=${OPENRCT2_VER} PATCH_FILE=${env.RESOLVED_PATCH}"
                }
            }
        }

        stage('Build Dependencies & OpenRCT2') {
            steps {
                echo "Compiling OpenRCT2 ${OPENRCT2_VER} with ${NUM_CORES} parallel jobs..."
                sh """
                    make all \
                        OPENRCT2_VERSION=${OPENRCT2_VER} \
                        PATCH_FILE=${env.RESOLVED_PATCH} \
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
                        OPENRCT2_VERSION=${OPENRCT2_VER} \
                        PATCH_FILE=${env.RESOLVED_PATCH}
                """
            }
        }

        stage('Package Release') {
            steps {
                echo "Packaging portable Windows XP release zip..."
                sh """
                    make package \
                        OPENRCT2_VERSION=${OPENRCT2_VER} \
                        PATCH_FILE=${env.RESOLVED_PATCH}
                """
            }
        }
    }

    post {
        success {
            echo "Build and XP compatibility check passed successfully!"
            archiveArtifacts artifacts: 'OpenRCT2-winxp*.zip, OpenRCT2/_build/openrct2.exe, OpenRCT2/_build/openrct2-cli.exe, OpenRCT2/_build/openrct2.com', fingerprint: true, allowEmptyArchive: false
        }
        failure {
            echo "Build or compatibility check failed. Please inspect console logs."
        }
    }
}

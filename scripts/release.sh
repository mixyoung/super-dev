#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[ERROR] python3/python not found in PATH"
    exit 1
fi

REPOSITORY="github"
RELEASE_GITHUB_REPO="mixyoung/super-dev"
ALLOW_DIRTY=0
SKIP_PREFLIGHT=0
SKIP_BENCHMARK=0
PUSH_TAG=0
SKIP_PUBLISH=0
CREATE_GITHUB_RELEASE=0
USE_GENERATED_NOTES=0
RELEASE_NOTES_FILE=""
RELEASE_TITLE=""
YES=0

usage() {
    cat <<'EOF'
Usage: ./scripts/release.sh [options]

Options:
  --repository <github|pypi|testpypi>  Target (default: github; PyPI requires explicit selection)
  --allow-dirty                 Allow dirty git worktree in preflight
  --skip-preflight              Skip preflight checks
  --skip-benchmark              Skip benchmark in preflight
  --skip-publish                Skip PyPI/TestPyPI publish; reuse existing dist artifacts
  --push-tag                    Create and push git tag v<version>
  --github-release              Create or update this fork's GitHub Release (otherwise prepare only)
  --generate-notes              Use GitHub generated release notes
  --notes-file <path>           Use a custom Markdown file for GitHub Release notes
  --title <text>                Override GitHub Release title
  --yes                         Non-interactive mode (no confirmation prompt)
  -h, --help                    Show this help

Environment:
  PYPI_API_TOKEN                API token for PyPI upload
  TEST_PYPI_API_TOKEN           API token for TestPyPI upload (fallback: PYPI_API_TOKEN)
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repository)
            REPOSITORY="${2:-}"
            shift 2
            ;;
        --allow-dirty)
            ALLOW_DIRTY=1
            shift
            ;;
        --skip-preflight)
            SKIP_PREFLIGHT=1
            shift
            ;;
        --skip-benchmark)
            SKIP_BENCHMARK=1
            shift
            ;;
        --skip-publish)
            SKIP_PUBLISH=1
            shift
            ;;
        --push-tag)
            PUSH_TAG=1
            shift
            ;;
        --github-release)
            CREATE_GITHUB_RELEASE=1
            shift
            ;;
        --generate-notes)
            USE_GENERATED_NOTES=1
            shift
            ;;
        --notes-file)
            RELEASE_NOTES_FILE="${2:-}"
            shift 2
            ;;
        --title)
            RELEASE_TITLE="${2:-}"
            shift 2
            ;;
        --yes)
            YES=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "[ERROR] Unknown argument: $1"
            usage
            exit 2
            ;;
    esac
done

if [[ "$REPOSITORY" != "github" && "$REPOSITORY" != "pypi" && "$REPOSITORY" != "testpypi" ]]; then
    echo "[ERROR] --repository must be github, pypi or testpypi"
    exit 2
fi

if [[ "$USE_GENERATED_NOTES" -eq 1 && -n "$RELEASE_NOTES_FILE" ]]; then
    echo "[ERROR] --generate-notes and --notes-file cannot be used together"
    exit 2
fi

if [[ -n "$RELEASE_NOTES_FILE" && ! -f "$RELEASE_NOTES_FILE" ]]; then
    echo "[ERROR] --notes-file not found: $RELEASE_NOTES_FILE"
    exit 2
fi

VERSION="$("$PYTHON_BIN" -c "from super_dev import __version__; print(__version__)")"
TAG="v${VERSION}"
BRANCH="$(git branch --show-current 2>/dev/null || true)"
WHEEL_PATH="dist/super_dev-${VERSION}-py3-none-any.whl"
SDIST_PATH="dist/super_dev-${VERSION}.tar.gz"

echo "[INFO] Release version: ${VERSION}"
echo "[INFO] Current branch: ${BRANCH:-unknown}"
echo "[INFO] Target repository: ${REPOSITORY}"

if [[ "$ALLOW_DIRTY" -ne 1 && -n "$(git status --porcelain)" ]]; then
    echo "[ERROR] Working tree is dirty. Commit or stash changes, or use --allow-dirty."
    exit 1
fi

if [[ "$YES" -ne 1 ]]; then
    read -r -p "Proceed with release ${VERSION}? (y/N): " confirm
    if [[ "${confirm,,}" != "y" ]]; then
        echo "[INFO] Release cancelled"
        exit 0
    fi
fi

if [[ "$SKIP_PUBLISH" -eq 1 ]]; then
    echo "[INFO] Publish step skipped by --skip-publish"
    if [[ ! -f "$WHEEL_PATH" || ! -f "$SDIST_PATH" ]]; then
        echo "[ERROR] Expected release artifacts are missing:"
        echo "  - $WHEEL_PATH"
        echo "  - $SDIST_PATH"
        echo "[ERROR] Rebuild first or run without --skip-publish"
        exit 1
    fi
elif [[ "$REPOSITORY" == "github" ]]; then
    # Keep the existing validation/build steps, without invoking PyPI upload.
    if [[ "$SKIP_PREFLIGHT" -ne 1 ]]; then
        PREFLIGHT_ARGS=("./scripts/preflight.sh" "--skip-package")
        if [[ "$ALLOW_DIRTY" -eq 1 ]]; then PREFLIGHT_ARGS+=("--allow-dirty"); fi
        if [[ "$SKIP_BENCHMARK" -eq 1 ]]; then PREFLIGHT_ARGS+=("--skip-benchmark"); fi
        "${PREFLIGHT_ARGS[@]}"
    fi
    "$PYTHON_BIN" -m build
    "$PYTHON_BIN" -m twine check "$WHEEL_PATH" "$SDIST_PATH"
else
    PUBLISH_ARGS=("./scripts/publish.sh" "--repository" "$REPOSITORY")
    if [[ "$ALLOW_DIRTY" -eq 1 ]]; then
        PUBLISH_ARGS+=("--allow-dirty")
    fi
    if [[ "$SKIP_PREFLIGHT" -eq 1 ]]; then
        PUBLISH_ARGS+=("--skip-preflight")
    fi
    if [[ "$SKIP_BENCHMARK" -eq 1 ]]; then
        PUBLISH_ARGS+=("--skip-benchmark")
    fi
    if [[ "$YES" -eq 1 ]]; then
        PUBLISH_ARGS+=("--yes")
    fi

    echo "[INFO] Running publish step"
    "${PUBLISH_ARGS[@]}"
fi

if [[ "$PUSH_TAG" -eq 1 ]]; then
    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "[ERROR] Git tag ${TAG} already exists"
        exit 1
    fi
    echo "[INFO] Creating git tag ${TAG}"
    git tag -a "$TAG" -m "Release ${VERSION}"
    git push origin "$TAG"
    echo "[PASS] Git tag pushed: ${TAG}"
else
    echo "[INFO] Tag step skipped (use --push-tag to enable)"
fi

if [[ "$CREATE_GITHUB_RELEASE" -eq 1 ]]; then
    if ! command -v gh >/dev/null 2>&1; then
        echo "[ERROR] gh is not installed; cannot create GitHub Release"
        exit 1
    fi

    TITLE="${RELEASE_TITLE:-$TAG}"
    ASSETS=()
    if [[ -f "$WHEEL_PATH" ]]; then
        ASSETS+=("$WHEEL_PATH")
    fi
    if [[ -f "$SDIST_PATH" ]]; then
        ASSETS+=("$SDIST_PATH")
    fi

    # The fork updater requires this checksum asset; compute it from these artifacts.
    "$PYTHON_BIN" -c 'import hashlib, pathlib, sys; files = [pathlib.Path(p) for p in sys.argv[1:]]; pathlib.Path("dist/SHA256SUMS.txt").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in files), encoding="utf-8")' "$WHEEL_PATH" "$SDIST_PATH"
    ASSETS+=("dist/SHA256SUMS.txt")

    if gh release view "$TAG" --repo "$RELEASE_GITHUB_REPO" >/dev/null 2>&1; then
        echo "[INFO] GitHub Release exists; updating ${TAG}"
        EDIT_ARGS=("$TAG" "--title" "$TITLE")
        if [[ -n "$RELEASE_NOTES_FILE" ]]; then
            EDIT_ARGS+=("--notes-file" "$RELEASE_NOTES_FILE")
        fi
        gh release edit "${EDIT_ARGS[@]}" --repo "$RELEASE_GITHUB_REPO"
        if [[ "${#ASSETS[@]}" -gt 0 ]]; then
            gh release upload "$TAG" "${ASSETS[@]}" --clobber --repo "$RELEASE_GITHUB_REPO"
        fi
        echo "[PASS] GitHub Release updated: ${TAG}"
    else
        echo "[INFO] Creating GitHub Release ${TAG}"
        CREATE_ARGS=("$TAG" "--verify-tag" "--title" "$TITLE")
        if [[ -n "$RELEASE_NOTES_FILE" ]]; then
            CREATE_ARGS+=("--notes-file" "$RELEASE_NOTES_FILE")
        elif [[ "$USE_GENERATED_NOTES" -eq 1 || -z "$RELEASE_NOTES_FILE" ]]; then
            CREATE_ARGS+=("--generate-notes")
        fi
        if [[ "${#ASSETS[@]}" -gt 0 ]]; then
            CREATE_ARGS+=("${ASSETS[@]}")
        fi
        gh release create "${CREATE_ARGS[@]}" --repo "$RELEASE_GITHUB_REPO"
        echo "[PASS] GitHub Release created: ${TAG}"
    fi
fi

if [[ "$REPOSITORY" == "github" && "$CREATE_GITHUB_RELEASE" -ne 1 ]]; then
    echo "[PASS] Artifacts prepared for ${RELEASE_GITHUB_REPO}; no GitHub Release published (use --github-release)"
else
    echo "[PASS] Release flow completed for ${VERSION}"
fi

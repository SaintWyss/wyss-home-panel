#!/usr/bin/env bash
set -Eeuo pipefail

readonly EXIT_CODE=10
readonly EXIT_DEPENDENCY=20
readonly EXIT_ENVIRONMENT=30
readonly EXIT_EVIDENCE=40

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly ROOT
readonly MANIFEST="$ROOT/config/baseline-versions.toml"
readonly CACHE_ROOT="$ROOT/.cache/wyss-baseline"

manifest_value() {
  local key="$1"
  sed -nE "s/^${key}[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\1/p" "$MANIFEST" | head -n 1
}

fail() {
  local code="$1"
  shift
  printf 'baseline: %s\n' "$*" >&2
  exit "$code"
}

require_tool() {
  command -v "$1" >/dev/null 2>&1 || fail "$EXIT_ENVIRONMENT" "falta la herramienta requerida: $1"
}

run_code() {
  "$@" || fail "$EXIT_CODE" "falló un build, análisis o test"
}

run_dependency() {
  "$@" || fail "$EXIT_DEPENDENCY" "falló la resolución de dependencias"
}

readonly PYTHON_VERSION="$(manifest_value python)"
readonly CMAKE_VERSION="$(manifest_value cmake)"
readonly UV_VERSION="$(manifest_value uv)"
readonly PLATFORMIO_VERSION="$(manifest_value platformio)"
readonly FIRMWARE_ENV="$(manifest_value environment)"

[[ -n "$PYTHON_VERSION" && -n "$CMAKE_VERSION" && -n "$UV_VERSION" && -n "$PLATFORMIO_VERSION" && -n "$FIRMWARE_ENV" ]] || \
  fail "$EXIT_ENVIRONMENT" "manifest de versiones incompleto"

export UV_CACHE_DIR="$CACHE_ROOT/uv"
export UV_PROJECT_ENVIRONMENT="$CACHE_ROOT/venv"
export PLATFORMIO_CORE_DIR="$CACHE_ROOT/platformio"
readonly CMAKE_BUILD_DIR="$CACHE_ROOT/cmake"
readonly TOOL_BIN="$CACHE_ROOT/bin"
mkdir -p "$UV_CACHE_DIR" "$PLATFORMIO_CORE_DIR" "$CMAKE_BUILD_DIR" "$TOOL_BIN"

require_tool uv
require_tool pio
require_tool c++

[[ "$(uv --version 2>/dev/null)" == "uv $UV_VERSION "* || "$(uv --version 2>/dev/null)" == "uv $UV_VERSION" ]] || \
  fail "$EXIT_ENVIRONMENT" "uv no coincide con la versión registrada"
[[ "$(pio --version 2>/dev/null)" == *"$PLATFORMIO_VERSION"* ]] || \
  fail "$EXIT_ENVIRONMENT" "PlatformIO no coincide con la versión registrada"

cat >"$TOOL_BIN/cmake" <<EOF
#!/usr/bin/env bash
exec uvx --from cmake==${CMAKE_VERSION} cmake "\$@"
EOF
chmod 0700 "$TOOL_BIN/cmake"
export PATH="$TOOL_BIN:$PATH"

cd "$ROOT"
run_dependency uv sync --project bridge --locked --extra dev --python "$PYTHON_VERSION"

run_code uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" ruff check bridge tools/check_docs.py tools/doctor.py
run_code uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" ruff format --check bridge tools/check_docs.py tools/doctor.py
run_code uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" mypy bridge/src
run_code uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" pytest bridge/tests --quiet

run_code uvx --from "cmake==$CMAKE_VERSION" cmake -S . -B "$CMAKE_BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
run_code uvx --from "cmake==$CMAKE_VERSION" cmake --build "$CMAKE_BUILD_DIR" --parallel
run_code uvx --from "cmake==$CMAKE_VERSION" ctest --test-dir "$CMAKE_BUILD_DIR" --output-on-failure
run_code pio run -e "$FIRMWARE_ENV"
run_code uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" python tools/doctor.py --format json
run_code uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" python tools/check_docs.py --format json

case "${1:-automated}" in
  automated)
    ;;
  all)
    [[ -f "$ROOT/tools/check_baseline_evidence.py" ]] || fail "$EXIT_EVIDENCE" "falta el verificador de evidencia física"
    uv run --project bridge --locked --extra dev --python "$PYTHON_VERSION" \
      python tools/check_baseline_evidence.py || fail "$EXIT_EVIDENCE" "evidencia ausente o inválida"
    ;;
  *)
    fail "$EXIT_ENVIRONMENT" "uso: $0 [automated|all]"
    ;;
esac

printf 'baseline: PASS (%s)\n' "${1:-automated}"

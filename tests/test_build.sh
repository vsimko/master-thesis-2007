#!/bin/sh
set -eu

# Test runner for build.sh
# Tests default build, clean, distclean/clean-all targets, and error handling.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_SH="$ROOT_DIR/build.sh"

PASSED=0
FAILED=0

run_test() {
  TEST_NAME="$1"
  shift
  printf "Running test: %s ... " "$TEST_NAME"
  if "$@"; then
    printf "PASSED\n"
    PASSED=$((PASSED + 1))
  else
    printf "FAILED\n"
    FAILED=$((FAILED + 1))
  fi
}

# Test 1: Invalid target exits with non-zero status code
test_invalid_target() {
  if "$BUILD_SH" invalid_target >/dev/null 2>&1; then
    return 1
  fi
  return 0
}

# Test 2: Clean target removes auxiliary files
test_clean_target() {
  cd "$ROOT_DIR"
  # Create dummy aux files
  touch dummy.aux main.log main.toc main.fls main.fdb_latexmk main.pdf
  "$BUILD_SH" clean >/dev/null 2>&1
  # Auxiliary files should be removed
  if [ -f dummy.aux ] || [ -f main.log ] || [ -f main.toc ] || [ -f main.fls ] || [ -f main.fdb_latexmk ]; then
    return 1
  fi
  # main.pdf must still exist after clean
  if [ ! -f main.pdf ]; then
    return 1
  fi
  rm -f main.pdf
  return 0
}

# Test 3: Distclean target removes auxiliary files and main.pdf
test_distclean_target() {
  cd "$ROOT_DIR"
  touch dummy.aux main.log main.pdf
  "$BUILD_SH" distclean >/dev/null 2>&1
  if [ -f dummy.aux ] || [ -f main.log ] || [ -f main.pdf ]; then
    return 1
  fi
  return 0
}

# Test 4: Clean-all alias works identically to distclean
test_clean_all_target() {
  cd "$ROOT_DIR"
  touch dummy.aux main.log main.pdf
  "$BUILD_SH" clean-all >/dev/null 2>&1
  if [ -f dummy.aux ] || [ -f main.log ] || [ -f main.pdf ]; then
    return 1
  fi
  return 0
}

# Test 5: Fallback path execution (pdflatex + bibtex) and default build target
test_build_fallback() {
  cd "$ROOT_DIR"
  "$BUILD_SH" distclean >/dev/null 2>&1
  # PATH without latexmk to test pdflatex/bibtex branch
  PATH="$(echo "$PATH" | tr ':' '\n' | grep -v 'latexmk' | tr '\n' ':')" "$BUILD_SH" build >/dev/null 2>&1
  if [ ! -f "$ROOT_DIR/main.pdf" ]; then
    return 1
  fi
  "$BUILD_SH" distclean >/dev/null 2>&1
  return 0
}

# Test 6: Default argument builds PDF
test_default_target_builds() {
  cd "$ROOT_DIR"
  "$BUILD_SH" distclean >/dev/null 2>&1
  "$BUILD_SH" >/dev/null 2>&1
  if [ ! -f "$ROOT_DIR/main.pdf" ]; then
    return 1
  fi
  "$BUILD_SH" distclean >/dev/null 2>&1
  return 0
}

# Test 7: Mocked latexmk branch execution
test_latexmk_branch() {
  MOCK_DIR="$(mktemp -d)"
  cat << 'EOF' > "$MOCK_DIR/latexmk"
#!/bin/sh
touch main.pdf
exit 0
EOF
  chmod +x "$MOCK_DIR/latexmk"

  cd "$ROOT_DIR"
  "$BUILD_SH" distclean >/dev/null 2>&1
  
  OUTPUT=$(PATH="$MOCK_DIR:$PATH" "$BUILD_SH" build 2>&1)
  rm -rf "$MOCK_DIR"

  if ! echo "$OUTPUT" | grep -q "Building using latexmk"; then
    return 1
  fi
  if [ ! -f "$ROOT_DIR/main.pdf" ]; then
    return 1
  fi
  "$BUILD_SH" distclean >/dev/null 2>&1
  return 0
}

echo "=== Running tests for build.sh ==="
run_test "Invalid target handling" test_invalid_target
run_test "Clean target removes aux files and preserves PDF" test_clean_target
run_test "Distclean target removes aux files and PDF" test_distclean_target
run_test "Clean-all alias target removes aux files and PDF" test_clean_all_target
run_test "Mocked latexmk build branch" test_latexmk_branch
run_test "Build fallback branch (pdflatex + bibtex)" test_build_fallback
run_test "Default build target without arguments" test_default_target_builds

echo "=== Test Summary: $PASSED passed, $FAILED failed ==="
if [ "$FAILED" -ne 0 ]; then
  exit 1
fi

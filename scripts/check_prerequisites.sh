#!/usr/bin/env bash
# Check development prerequisites for RT-AFF

set -e

WARNINGS=0
FAILURES=0

warn() {
    echo "⚠️  WARNING: $1"
    WARNINGS=$((WARNINGS + 1))
}

fail() {
    echo "❌ REQUIRED: $1"
    FAILURES=$((FAILURES + 1))
}

ok() {
    echo "✓ $1"
}

echo "Checking prerequisites..."
echo

# Python 3.11+
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        ok "Python $PY_VERSION"
    else
        fail "Python 3.11+ required (found $PY_VERSION)"
    fi
else
    fail "Python 3.11+ not found"
fi

# uv (fast Python package manager)
if command -v uv &> /dev/null; then
    ok "uv $(uv --version | awk '{print $2}')"
else
    fail "uv not found — install: brew install uv (or: curl -LsSf https://astral.sh/uv/install.sh | sh)"
fi

# Node.js 18+
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VERSION" -ge 18 ]; then
        ok "Node.js $(node -v)"
    else
        fail "Node.js 18+ required (found $(node -v))"
    fi
else
    fail "Node.js 18+ not found"
fi

# Docker or Podman
if command -v docker &> /dev/null; then
    ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
elif command -v podman &> /dev/null; then
    ok "Podman $(podman --version | awk '{print $3}')"
else
    fail "Docker or Podman not found"
fi

# fswatch for auto-reseed on schema changes (optional)
if command -v fswatch &> /dev/null; then
    ok "fswatch (schema file watching)"
else
    warn "fswatch not found — schema file watching disabled in 'make dev'. Install: brew install fswatch"
fi

# WeasyPrint native dependencies (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if brew list pango &> /dev/null; then
        ok "pango (for PDF generation)"
    else
        warn "pango not installed - local PDF tests will fail. Run: brew install pango gdk-pixbuf libffi"
    fi
fi

# WeasyPrint native dependencies (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if ldconfig -p 2>/dev/null | grep -q libpango; then
        ok "libpango (for PDF generation)"
    else
        warn "libpango not installed - local PDF tests will fail. Run: apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0"
    fi
fi

echo
echo "─────────────────────────────────"
if [ $FAILURES -gt 0 ]; then
    echo "❌ $FAILURES required prerequisite(s) missing"
    echo "   Setup cannot continue until these are resolved."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo "⚠️  $WARNINGS optional prerequisite(s) missing"
    echo "   Some functionality may be limited."
    exit 0
else
    echo "✓ All prerequisites satisfied"
    exit 0
fi

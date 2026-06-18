#!/bin/bash
# Build "Repertiores Suite.app" — one native window that launches BOTH the
# Repertiores (programming) and FBA Tracker (assessment) Streamlit apps behind a
# landing chooser.
#
# Data:   the Suite SHARES the existing Repertiores data dir so it uses your real
#         learners (the roster), and keeps FBA's own files in a /fba subdir so the
#         two students.json schemas never collide:
#           ~/Library/Application Support/Repertiores/data         (roster + Repertiores)
#           ~/Library/Application Support/Repertiores/data/fba      (FBA's files)
# Env:    the Suite's Python venv + logs live under a SEPARATE support dir so the
#         standalone Repertiores.app keeps working untouched:
#           ~/Library/Application Support/Repertiores Suite/venv
#
# Usage:  ./build_suite_app.sh
set -euo pipefail
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
FBA_DIR="$PROJECT_DIR/../fba_tracker📱"

APP_NAME="Repertiores Suite"
BUNDLE_ID="com.joeott.repertiores-suite"
VERSION="1.0.0"

DIST="$PROJECT_DIR/dist"
APP="$DIST/$APP_NAME.app"
SUPPORT="$HOME/Library/Application Support/$APP_NAME"
VENV="$SUPPORT/venv"
# Shared with the standalone Repertiores app:
REP_SUPPORT="$HOME/Library/Application Support/Repertiores"
DATA="$REP_SUPPORT/data"
FBA_DATA="$DATA/fba"

echo "▸ Building $APP_NAME.app"

# ── 1. Bundle skeleton ───────────────────────────────────────────────────────
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/src"

# Ship both app sources (renamed so they sit side by side) + the suite launcher.
# Never ship the local data/ (PHI) or backups.
cp app.py            "$APP/Contents/Resources/src/repertiores_app.py"
cp "$FBA_DIR/app.py" "$APP/Contents/Resources/src/fba_app.py"
cp desktop_suite.py  "$APP/Contents/Resources/src/desktop_suite.py"
cp requirements.txt  "$APP/Contents/Resources/src/requirements.txt"
cp "$FBA_DIR/requirements.txt" "$APP/Contents/Resources/src/requirements_fba.txt"
cp -R .streamlit "$APP/Contents/Resources/src/.streamlit"

# Optional icon: reuse Repertiores's if present.
ICON_LINE=""
if [ -f AppIcon.icns ]; then
  cp AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
  ICON_LINE="<key>CFBundleIconFile</key><string>AppIcon</string>"
fi

# ── 2. Info.plist ────────────────────────────────────────────────────────────
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleExecutable</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>$VERSION</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.medical</string>
  $ICON_LINE
  <key>NSAppTransportSecurity</key>
  <dict><key>NSAllowsLocalNetworking</key><true/></dict>
</dict>
</plist>
PLIST

# ── 3. Launcher (Contents/MacOS/Repertiores Suite) ───────────────────────────
cat > "$APP/Contents/MacOS/$APP_NAME" <<'LAUNCH'
#!/bin/bash
set -uo pipefail
APP_NAME="Repertiores Suite"
BUNDLE="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$BUNDLE/Contents/Resources/src"
SUPPORT="$HOME/Library/Application Support/$APP_NAME"
VENV="$SUPPORT/venv"
# Shared roster + Repertiores data; FBA gets its own subdir.
DATA="$HOME/Library/Application Support/Repertiores/data"
FBA_DATA="$DATA/fba"
LOG="$SUPPORT/launch.log"
READY="$VENV/.suite_ready"
mkdir -p "$SUPPORT" "$DATA" "$FBA_DATA"
exec >>"$LOG" 2>&1
echo "=== launch $(date) ==="

fail() {
  /usr/bin/osascript -e "display dialog \"Repertiores Suite could not start.\n\n$1\n\nSee: $LOG\" buttons {\"OK\"} with icon stop with title \"Repertiores Suite\"" || true
  exit 1
}

find_python() {
  for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    [ -x "$p" ] && { echo "$p"; return; }
  done
  command -v python3 2>/dev/null || true
}

if [ ! -x "$VENV/bin/python" ]; then
  PYBASE="$(find_python)"
  [ -n "$PYBASE" ] || fail "No Python 3 found. Install Python 3 (python.org or 'brew install python')."
  echo "Creating environment with $PYBASE (first launch, one-time)…"
  "$PYBASE" -m venv "$VENV" || fail "Could not create the Python environment."
fi
# Install/verify BOTH apps' dependencies (idempotent; marker skips it next time).
if [ ! -f "$READY" ]; then
  echo "Installing dependencies for both apps (one-time)…"
  "$VENV/bin/python" -m pip install --upgrade pip || fail "pip upgrade failed."
  "$VENV/bin/python" -m pip install -r "$SRC/requirements.txt" \
                                    -r "$SRC/requirements_fba.txt" pywebview \
    || fail "Dependency install failed (check your internet connection)."
  touch "$READY"
fi

export REPERTIORES_DATA_DIR="$DATA"
export FBA_DATA_DIR="$FBA_DATA"
exec "$VENV/bin/python" "$SRC/desktop_suite.py"
LAUNCH
chmod +x "$APP/Contents/MacOS/$APP_NAME"

# ── 4. Pre-build the environment so the first real launch is instant ─────────
echo "▸ Preparing Python environment in $SUPPORT (one-time, may take a few minutes)…"
find_python() {
  for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    [ -x "$p" ] && { echo "$p"; return; }
  done
  command -v python3 2>/dev/null || true
}
PYBASE="$(find_python)"
if [ -n "$PYBASE" ]; then
  [ -x "$VENV/bin/python" ] || "$PYBASE" -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r requirements.txt \
                                    -r "$FBA_DIR/requirements.txt" pywebview
  touch "$VENV/.suite_ready"
else
  echo "  (no base python found now — the app will build its env on first launch)"
fi

# ── 5. Seed FBA data into the shared dir on first build only ─────────────────
# (Repertiores's own data is assumed already present from the standalone app.)
if [ ! -d "$FBA_DATA" ] || [ -z "$(ls -A "$FBA_DATA" 2>/dev/null)" ]; then
  if [ -d "$FBA_DIR/data" ]; then
    echo "▸ Seeding FBA data → $FBA_DATA (from fba_tracker📱/data/)"
    mkdir -p "$FBA_DATA"
    cp -R "$FBA_DIR/data/." "$FBA_DATA/"
  fi
else
  echo "▸ Existing FBA data found at $FBA_DATA — left untouched."
fi
if [ ! -e "$DATA/students.json" ]; then
  echo "  ⚠️ No Repertiores roster at $DATA/students.json — launch the standalone"
  echo "     Repertiores app once (or seed its data) so the Suite has a shared roster."
fi

echo
echo "✅ Built: $APP"
echo "   Suite venv + logs: $SUPPORT"
echo "   Shared data:       $DATA  (FBA files in $FBA_DATA)"
echo "   Install with:  cp -R \"$APP\" /Applications/"

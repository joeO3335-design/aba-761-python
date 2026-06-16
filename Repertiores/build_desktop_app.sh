#!/bin/bash
# Build a double-clickable "Repertiores.app" (native window, venv-bundled).
#
# The .app is a thin native bundle: it ships the Python source and a launcher.
# The Python environment and the learner data live in
#   ~/Library/Application Support/Repertiores/{venv,data}
# — a writable location, so the app keeps working when installed read-only in
# /Applications, and updating the app never touches the data.
#
# Usage:  ./build_desktop_app.sh
set -euo pipefail
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"

APP_NAME="Repertiores"
BUNDLE_ID="com.joeott.repertiores"
VERSION="1.0.0"

DIST="$PROJECT_DIR/dist"
APP="$DIST/$APP_NAME.app"
SUPPORT="$HOME/Library/Application Support/$APP_NAME"
VENV="$SUPPORT/venv"
DATA="$SUPPORT/data"

echo "▸ Building $APP_NAME.app"

# ── 1. Bundle skeleton ───────────────────────────────────────────────────────
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/src"

# Ship only what the app needs to run — never the local data/ (PHI) or backups.
cp app.py desktop_main.py requirements.txt "$APP/Contents/Resources/src/"
cp -R .streamlit "$APP/Contents/Resources/src/.streamlit"

# Optional icon: use AppIcon.icns if present, else generate from icon-1024.png.
ICON_LINE=""
if [ ! -f AppIcon.icns ] && [ -f icon-1024.png ]; then
  ICONSET=build_iconset/AppIcon.iconset
  rm -rf build_iconset && mkdir -p "$ICONSET"
  for sz in 16 32 64 128 256 512; do
    sips -z $sz $sz icon-1024.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
    d=$((sz*2)); sips -z $d $d icon-1024.png --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
  done
  cp icon-1024.png "$ICONSET/icon_512x512@2x.png"
  iconutil -c icns "$ICONSET" -o AppIcon.icns
  rm -rf build_iconset
fi
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

# ── 3. Launcher (Contents/MacOS/Repertiores) ─────────────────────────────────
# Finder-launched apps get a minimal PATH and no console, so we resolve a base
# python from known locations and log to the support dir for troubleshooting.
cat > "$APP/Contents/MacOS/$APP_NAME" <<'LAUNCH'
#!/bin/bash
set -uo pipefail
APP_NAME="Repertiores"
BUNDLE="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$BUNDLE/Contents/Resources/src"
SUPPORT="$HOME/Library/Application Support/$APP_NAME"
VENV="$SUPPORT/venv"
DATA="$SUPPORT/data"
LOG="$SUPPORT/launch.log"
mkdir -p "$SUPPORT" "$DATA"
exec >>"$LOG" 2>&1
echo "=== launch $(date) ==="

fail() {
  /usr/bin/osascript -e "display dialog \"Repertiores could not start.\n\n$1\n\nSee: $LOG\" buttons {\"OK\"} with icon stop with title \"Repertiores\"" || true
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
  "$VENV/bin/python" -m pip install --upgrade pip || fail "pip upgrade failed."
  "$VENV/bin/python" -m pip install -r "$SRC/requirements.txt" pywebview \
    || fail "Dependency install failed (check your internet connection)."
fi

export REPERTIORES_DATA_DIR="$DATA"
exec "$VENV/bin/python" "$SRC/desktop_main.py"
LAUNCH
chmod +x "$APP/Contents/MacOS/$APP_NAME"

# ── 4. Pre-build the environment so the first real launch is instant ─────────
echo "▸ Preparing Python environment in $SUPPORT (one-time, may take a minute)…"
find_python() {
  for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    [ -x "$p" ] && { echo "$p"; return; }
  done
  command -v python3 2>/dev/null || true
}
PYBASE="$(find_python)"
if [ -n "$PYBASE" ]; then
  if [ ! -x "$VENV/bin/python" ]; then
    "$PYBASE" -m venv "$VENV"
  fi
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r requirements.txt pywebview
else
  echo "  (no base python found now — the app will build its env on first launch)"
fi

# ── 5. Seed learner data from the dev folder on first build only ─────────────
if [ ! -d "$DATA" ] || [ -z "$(ls -A "$DATA" 2>/dev/null)" ]; then
  if [ -d "$PROJECT_DIR/data" ]; then
    echo "▸ Seeding data → $DATA (copied from the project's data/ folder)"
    mkdir -p "$DATA"
    cp -R "$PROJECT_DIR/data/." "$DATA/"
  fi
else
  echo "▸ Existing app data found at $DATA — left untouched."
fi

echo
echo "✅ Built: $APP"
echo "   Data + environment live in: $SUPPORT"
echo "   Install with:  cp -R \"$APP\" /Applications/"

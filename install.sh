#!/usr/bin/env sh
# Installs youtube-creator-kit into Claude Code (macOS / Linux). Run again to update.
# Your filled-in ~/.claude/youtube/channels.md is never overwritten.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/skills/youtube-creator-kit"
DST="$HOME/.claude/skills/youtube-creator-kit"
PROFILE="$HOME/.claude/youtube/channels.md"
PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || { echo "Python 3 is needed: https://www.python.org/downloads/"; exit 1; }

echo "Running tests first..."
"$PY" "$HERE/tests/test_tools.py" || { echo "TESTS FAILED - nothing installed."; exit 1; }

rm -rf "$DST"
mkdir -p "$HOME/.claude/skills"
cp -R "$SRC" "$DST"
if [ ! -f "$PROFILE" ]; then
  mkdir -p "$(dirname "$PROFILE")"
  cp "$SRC/channels.template.md" "$PROFILE"
  echo "Created $PROFILE - fill in the blanks."
fi
echo
echo "Installed to $DST"
echo "Start a NEW Claude Code session, then ask for help with titles, or type /youtube-creator-kit"

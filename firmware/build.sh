#!/usr/bin/env bash
# Build the cube firmware: WLED (pinned in WLED_VERSION) + AudioReactive + cube_ui.
#
#   firmware/build.sh            build; binaries land in firmware/dist/
#   firmware/build.sh upload     build and flash over USB (PlatformIO picks the port)
#
# The WLED checkout lives in firmware/.wled (gitignored). The usermod is symlinked into it,
# so edits under firmware/usermods/ are picked up on the next build. WLED's own build
# scripts run `npm ci && npm run build` for the web UI, so Node.js must be installed.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
wled_version="$(tr -d '[:space:]' < "$here/WLED_VERSION")"
wled="$here/.wled"

if [[ ! -d "$wled/.git" ]]; then
  git clone --depth 1 --branch "$wled_version" https://github.com/wled/WLED.git "$wled"
elif [[ "$(git -C "$wled" describe --tags --exact-match 2>/dev/null || true)" != "$wled_version" ]]; then
  git -C "$wled" fetch --depth 1 origin tag "$wled_version"
  git -C "$wled" checkout -q "$wled_version"
fi

ln -sfn "$here/usermods/cube_ui" "$wled/usermods/cube_ui"
cp "$here/platformio_override.ini" "$wled/platformio_override.ini"

pio_cmd=(pio)
command -v pio >/dev/null 2>&1 || pio_cmd=(uvx --from platformio pio)

cd "$wled"
if [[ "${1:-}" == "upload" ]]; then
  "${pio_cmd[@]}" run -e cube_esp32 -t upload
else
  "${pio_cmd[@]}" run -e cube_esp32
fi

"$here/package.sh"

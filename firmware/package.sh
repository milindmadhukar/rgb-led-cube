#!/usr/bin/env bash
# Collect the build outputs into firmware/dist/:
#   ledcube-wled-<wled>_<ver>_<release>.bin           app only: OTA from WLED (Config > Security & Updates)
#   ledcube-wled-<wled>_<ver>_<release>_factory.bin   bootloader + partitions + app: flash a blank ESP32 at 0x0
#
# <ver> is the tag without its leading "v" and <release> is WLED_RELEASE_NAME. WLED's "Auto update"
# button looks for an asset ending in _<ver>_<release>.bin, so keep the OTA name in that shape.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
wled="$here/.wled"
build="$wled/.pio/build/cube_esp32"
wled_ver="$(tr -d '[:space:]' < "$here/WLED_VERSION")"
tag="${CUBE_FW_TAG:-$(git -C "$here" describe --tags --always --dirty 2>/dev/null || echo dev)}"
ver="${tag#v}"
release="$(sed -n 's/.*WLED_RELEASE_NAME=\\"\([^\\]*\)\\".*/\1/p' "$here/platformio_override.ini")"
[[ -n "$release" ]] || { echo "error: WLED_RELEASE_NAME not found in platformio_override.ini" >&2; exit 1; }
name="ledcube-wled-${wled_ver}_${ver}_${release}"
mkdir -p "$here/dist"

cp "$build/firmware.bin" "$here/dist/${name}.bin"

boot_app0="$(find "$HOME/.platformio/packages" -path '*partitions/boot_app0.bin' 2>/dev/null | head -1)"
if [[ -n "$boot_app0" && -f "$build/bootloader.bin" && -f "$build/partitions.bin" ]]; then
  esptool=(python3 -m esptool)
  python3 -c 'import esptool' 2>/dev/null || esptool=(uvx esptool)
  "${esptool[@]}" --chip esp32 merge-bin -o "$here/dist/${name}_factory.bin" \
    --flash-mode dio --flash-size 4MB \
    0x1000 "$build/bootloader.bin" 0x8000 "$build/partitions.bin" \
    0xe000 "$boot_app0" 0x10000 "$build/firmware.bin"
else
  echo "warning: bootloader/partitions/boot_app0 not found; factory image skipped" >&2
fi
ls -la "$here/dist"

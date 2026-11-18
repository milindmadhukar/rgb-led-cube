#!/usr/bin/env bash
# Collect the build outputs into firmware/dist/:
#   ledcube-<ver>-ota.bin       app only: upload from WLED's web UI (Config > Security & Updates)
#   ledcube-<ver>-factory.bin   bootloader + partitions + app: flash a blank ESP32 at 0x0
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
wled="$here/.wled"
build="$wled/.pio/build/cube_esp32"
ver="$(tr -d '[:space:]' < "$here/WLED_VERSION")"
tag="${CUBE_FW_TAG:-$(git -C "$here" describe --tags --always --dirty 2>/dev/null || echo dev)}"
name="ledcube-wled-${ver}-${tag}"
mkdir -p "$here/dist"

cp "$build/firmware.bin" "$here/dist/${name}-ota.bin"

boot_app0="$(find "$HOME/.platformio/packages" -path '*partitions/boot_app0.bin' 2>/dev/null | head -1)"
if [[ -n "$boot_app0" && -f "$build/bootloader.bin" && -f "$build/partitions.bin" ]]; then
  esptool=(python3 -m esptool)
  python3 -c 'import esptool' 2>/dev/null || esptool=(uvx esptool)
  "${esptool[@]}" --chip esp32 merge-bin -o "$here/dist/${name}-factory.bin" \
    --flash-mode dio --flash-size 4MB \
    0x1000 "$build/bootloader.bin" 0x8000 "$build/partitions.bin" \
    0xe000 "$boot_app0" 0x10000 "$build/firmware.bin"
else
  echo "warning: bootloader/partitions/boot_app0 not found; factory image skipped" >&2
fi
ls -la "$here/dist"

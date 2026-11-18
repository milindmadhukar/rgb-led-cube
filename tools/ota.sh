#!/usr/bin/env bash
# Flash the cube over Wi-Fi through WLED's /update endpoint.
#
#   tools/ota.sh <host>                latest GitHub release
#   tools/ota.sh <host> v0.2.0         a specific release tag
#   tools/ota.sh <host> path/to.bin    a local build (firmware/dist/*_LEDCube_ESP32.bin)
#
# <host> is the cube's IP address or mDNS name (WLED: Config → WiFi Setup → mDNS address).
# CUBE_HOST can stand in for it. Releases are public, so no GitHub login is needed.
# WLED refuses the upload if the binary's release name isn't LEDCube_ESP32, so a stock
# WLED build can't overwrite the cube by accident.
set -euo pipefail

repo="milindmadhukar/rgb-led-cube"
here="$(cd "$(dirname "$0")" && pwd)"
release="$(sed -n 's/.*WLED_RELEASE_NAME=\\"\([^\\]*\)\\".*/\1/p' "$here/../firmware/platformio_override.ini")"
release="${release:-LEDCube_ESP32}"

usage() { sed -n '2,11s/^# \{0,1\}//p' "$0" >&2; exit 2; }

host="${1:-${CUBE_HOST:-}}"
[[ -n "$host" && "$host" != -h && "$host" != --help ]] || usage
what="${2:-latest}"

tmp="$(mktemp -d -t cube-ota.XXXXXX)"
trap 'rm -rf "$tmp"' EXIT

if [[ -f "$what" ]]; then
  bin="$what"
else
  if [[ "$what" == latest ]]; then
    api="https://api.github.com/repos/$repo/releases/latest"
  else
    api="https://api.github.com/repos/$repo/releases/tags/$what"
  fi
  curl -fsSL "$api" -o "$tmp/release.json" || { echo "error: no release '$what' in $repo" >&2; exit 1; }
  read -r tag name url < <(python3 -I -c '
import json, sys
rel = json.load(open(sys.argv[1]))
suffix = "_" + sys.argv[2] + ".bin"
assets = [a for a in rel["assets"] if a["name"].endswith(suffix)]
if not assets:
    sys.exit("error: release %s has no *%s asset" % (rel["tag_name"], suffix))
print(rel["tag_name"], assets[0]["name"], assets[0]["browser_download_url"])
' "$tmp/release.json" "$release")
  echo "Downloading $name ($tag)"
  curl -fL --progress-bar -o "$tmp/$name" "$url"
  bin="$tmp/$name"
fi

echo "Uploading $(basename "$bin") to http://$host/update"
code="$(curl -sS --max-time 300 -o "$tmp/resp.html" -w '%{http_code}' -F "update=@$bin" "http://$host/update")" || {
  echo "error: could not reach http://$host/update" >&2; exit 1; }

# WLED answers with a small HTML page; strip the tags to get its message.
msg="$(sed -e 's/<[^>]*>/ /g' "$tmp/resp.html" | tr -s ' \n' ' ' | sed 's/^ *//')"
if [[ "$code" == 200 ]]; then
  echo "OK: the cube is rebooting into the new firmware."
else
  echo "error: HTTP $code from the cube: ${msg:0:300}" >&2
  [[ "$code" == 401 ]] && echo "hint: unlock OTA / enter the settings PIN in Config → Security & Updates" >&2
  exit 1
fi

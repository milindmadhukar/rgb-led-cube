# RGB LED Cube

An 8×8×8 cube of WS2812D-F8 LEDs: 8 slabs, each on its own ESP32 data output, running WLED with
AudioReactive and a custom front panel (128×64 OLED, a knob and a button).

The design notes live in the Obsidian vault. `docs/` is a local symlink to them and is not committed.

## Layout

```
firmware/
  WLED_VERSION              pinned WLED release (v16.0.1)
  platformio_override.ini   the cube_esp32 build: pins, LED counts, usermods
  usermods/cube_ui/         OLED + knob + button usermod
  build.sh                  fetch WLED, link the usermod, build, package
  package.sh                OTA bin + factory bin into firmware/dist/
.github/workflows/firmware.yml   CI build; tags v* publish a release
```

## Build

Needs Node.js ≥ 20 and PlatformIO (`uv tool install platformio`; the script falls back to `uvx`).

```bash
firmware/build.sh           # → firmware/dist/ledcube-wled-v16.0.1_<ver>_LEDCube_ESP32{,_factory}.bin
firmware/build.sh upload    # build and flash over USB
```

The first build downloads the ESP32 toolchain, so it takes a while.

## Flash

- **Blank ESP32:** `esptool --chip esp32 write_flash 0x0 firmware/dist/*_factory.bin`
- **Already running WLED:** Config → Security & Updates → upload `*_LEDCube_ESP32.bin`

## First boot

1. Join the `WLED-AP` Wi-Fi (password `wled1234`) and set up your network.
2. **LED Preferences** should already show 8 outputs (GPIO 16, 17, 18, 19, 23, 25, 26, 27) × 64 LEDs, with the current limit at 9 A. Button 0 should be on GPIO13 (*Pushbutton*).
3. **Usermods → AudioReactive:** tick *Enabled*. The mic pins (SD 32, WS 15, SCK 14) are preset.
4. **Usermods → CubeUI:** turn the knob fully both ways, read the raw values on the Info page, and enter them as `knob-raw-min` / `knob-raw-max`.

## Releases

Push a tag such as `v1.0.0`. CI builds it and attaches both binaries to a GitHub release.

## Updating over the air

The firmware knows its repo (`WLED_REPO` in `platformio_override.ini`), so the cube can install the
latest release itself: **Config → Security & Updates → Auto update**. The browser fetches the release's
`*_LEDCube_ESP32.bin` from GitHub (through WLED's `download.wled.me` relay) and uploads it to the cube,
so the device you click from needs internet access.

- Auto update always installs the latest release; it does not compare versions. Pre-releases are skipped.
- WLED checks the release name (`LEDCube_ESP32`) on upload, so a stock WLED build cannot overwrite the cube
  by mistake (for example from Home Assistant's WLED update entity).
- A cube running a build from before `WLED_REPO` was set points at `wled/WLED`. Upload one new
  `*_LEDCube_ESP32.bin` by hand once; Auto update works from then on.

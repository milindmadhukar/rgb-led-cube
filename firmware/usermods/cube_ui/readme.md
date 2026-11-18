# cube_ui: OLED + knob front panel for the LED cube

A WLED v16 usermod that drives a 128×64 I²C OLED (SSD1306 0.96″ or SH1106 1.3″), reads one
linear potentiometer, and takes over WLED's Button 0.

| Input | Action |
|---|---|
| Knob | Sets the value of the current mode: **Brightness → Effect → Palette → Speed → Intensity** |
| Short press | Next mode |
| Long press (0.7 s) | Power on/off |
| Anything while the screen is asleep | Wakes it (that input isn't applied) |

## How the knob behaves

- **Absolute, with soft takeover.** A pot can't be "re-zeroed" the way an encoder can. So after a mode change, or after the value was changed from the app, the knob **doesn't take control until it's turned through the current value**. Until then the screen shows a ▲ under the bar for the knob's position and says which way to turn. Nothing ever jumps.
- **Effects and palettes** are in alphabetical order, with Solid / Default and the dynamic palettes first. The name updates live while turning, and the change is **applied once the knob has been still for 0.35 s**.
- **Brightness** goes from 1 to 255. The knob never turns the cube off; that's the long press.
- **Noise:** 8× oversampling, a running average and a dead band (default 0.8% of travel).

## Wiring

| Part | Pin |
|---|---|
| Pot wiper | GPIO34. It must be ADC1 (GPIO32–39), because ADC2 stops working when Wi-Fi is on. |
| Pot ends | 3V3 and GND. Add a 100 nF cap from the wiper to GND. |
| OLED | SDA 21, SCL 22 (WLED's global I²C pins), 3V3, GND |
| Button | WLED Button 0 = GPIO13 to GND, type *Pushbutton* |

## Settings (Config → Usermods → CubeUI)

| Setting | Meaning |
|---|---|
| `pin` | Pot wiper GPIO |
| `button` | Which WLED button to take over (index) |
| `display-type` | 0 = SSD1306, 1 = SH1106 |
| `i2c-address` | 60 (0x3C) or 61 (0x3D) |
| `flip` | Rotate the display 180° |
| `contrast` | 0–255 |
| `sleep-s` | Turn the display off after this many seconds idle (0 = never) |
| `knob-raw-min` / `knob-raw-max` | Calibration: the Info page shows the knob's raw reading. Put in the readings at both ends. |
| `deadband-pm` | Noise band, in tenths of a percent |
| `apply-to-all` | Change every active segment, or only the main one |
| `audio-spectrum` | 16-band spectrum in the status line. Off by default: each refresh holds the I²C bus for ~25 ms. |

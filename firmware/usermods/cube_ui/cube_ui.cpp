/*
 * cube_ui: front-panel UI for the RGB LED Cube (WLED v16 usermod).
 *
 * Hardware: one 128x64 I2C OLED (SSD1306 or SH1106), one linear potentiometer on an
 * ADC1 pin, and WLED's own Button 0 (a momentary push button).
 *
 * Controls:
 *   knob          sets the value of the current mode (absolute, with soft takeover)
 *   short press   next mode: Brightness -> Effect -> Palette -> Speed -> Intensity
 *   long press    power on/off
 *   any input     wakes the display first if it is asleep (that input is not applied)
 *
 * Soft takeover: when the mode changes, or the value is changed from the app, the knob's
 * position rarely matches the value. The knob only takes control once it has been turned
 * through the current value, so nothing ever jumps. Until then the screen shows where the
 * knob is against where the value is.
 *
 * Effect and palette changes are previewed on screen and applied once the knob has been
 * still for a moment, so sweeping past twenty effects doesn't restart twenty effects.
 *
 * Written for this project with an AI assistant (Claude); reviewed and built against
 * WLED v16.0.1.
 */
#include "wled.h"
#include <U8g2lib.h>
#include <Wire.h>
#include <vector>
#include <algorithm>

#ifndef CUBEUI_POT_PIN
  #define CUBEUI_POT_PIN 34
#endif
#ifndef CUBEUI_BUTTON
  #define CUBEUI_BUTTON 0
#endif

class CubeUiUsermod : public Usermod {
  private:
    enum Mode : uint8_t { M_BRI = 0, M_FX, M_PAL, M_SPD, M_INT, M_COUNT };

    // ---- settings (Usermod settings page) ----
    bool     enabled      = true;
    int8_t   potPin       = CUBEUI_POT_PIN;
    uint8_t  buttonIndex  = CUBEUI_BUTTON;
    uint8_t  displayType  = 0;      // 0 = SSD1306 128x64, 1 = SH1106 128x64
    uint8_t  i2cAddress   = 0x3C;
    bool     flip         = false;
    uint8_t  contrast     = 160;
    uint16_t sleepSeconds = 120;    // 0 = never
    uint16_t rawMin       = 120;    // ADC reading at the knob's minimum
    uint16_t rawMax       = 3970;   // ADC reading at the knob's maximum
    uint8_t  deadband     = 8;      // per-mille of travel ignored as noise
    bool     applyToAll   = true;   // change every active segment, not just the main one
    bool     showAudio    = false;  // tiny spectrum in the status line (costs I2C time)

    // ---- runtime ----
    bool     initDone     = false;
    bool     potOk        = false;
    U8G2    *u8g2         = nullptr;
    bool     asleep       = false;
    bool     needRedraw   = true;
    uint32_t lastActivity = 0;
    uint32_t lastDraw     = 0;
    uint32_t lastPotRead  = 0;
    uint32_t lastApply    = 0;
    uint32_t lastKnobMove = 0;

    Mode     mode         = M_BRI;
    float    filt         = -1.0f;  // filtered raw ADC value
    int16_t  knobPm       = 0;      // reported knob position, 0..1000
    int16_t  prevKnobPm   = 0;
    bool     captured     = false;
    int16_t  lastSetPm    = -1;     // value we last applied, to detect outside changes
    int16_t  pendingIdx   = -1;     // effect/palette list index waiting to be applied

    bool     btnDown      = false;
    bool     longFired    = false;
    uint32_t btnDownAt    = 0;

    std::vector<uint8_t> fxList;    // effect ids, Solid first, the rest A-Z, reserved slots removed
    std::vector<uint8_t> palList;   // palette ids, built-in dynamic ones first, the rest A-Z

    static const char _name[];

    // ------------------------------------------------------------------ helpers
    static int16_t clampPm(int v) { return v < 0 ? 0 : (v > 1000 ? 1000 : v); }

    Segment& seg() { return strip.getMainSegment(); }

    void touch() { lastActivity = millis(); needRedraw = true; }

    // Returns true if the display was asleep (the caller should then ignore the input).
    bool wake() {
      lastActivity = millis();
      if (u8g2 && asleep) {
        asleep = false;
        u8g2->setPowerSave(0);
        needRedraw = true;
        return true;
      }
      return false;
    }

    template <typename F> void forSegments(F fn) {
      if (applyToAll) {
        for (unsigned i = 0; i < strip.getSegmentsNum(); i++) {
          Segment& s = strip.getSegment(i);
          if (s.isActive()) fn(s);
        }
      } else {
        fn(seg());
      }
    }

    void announce() {
      stateChanged = true;
      stateUpdated(CALL_MODE_BUTTON);
      updateInterfaces(CALL_MODE_BUTTON);
    }

    // ---- name lists ----
    struct Named { uint8_t id; char name[28]; };

    static bool byName(const Named& a, const Named& b) { return strcasecmp(a.name, b.name) < 0; }

    void buildLists() {
      std::vector<Named> tmp;
      char buf[28];

      fxList.clear();
      tmp.reserve(strip.getModeCount());
      for (unsigned id = 1; id < strip.getModeCount(); id++) {
        uint8_t len = extractModeName(id, JSON_mode_names, buf, sizeof(buf) - 1);
        if (!len || buf[0] == '-' || strncmp_P(buf, PSTR("RSVD"), 4) == 0) continue;
        Named n; n.id = id; strlcpy(n.name, buf, sizeof(n.name)); tmp.push_back(n);
      }
      std::sort(tmp.begin(), tmp.end(), byName);
      fxList.push_back(0);  // Solid stays at the knob's minimum
      for (auto& n : tmp) fxList.push_back(n.id);

      tmp.clear();
      palList.clear();
      for (unsigned id = 0; id < FIXED_PALETTE_COUNT; id++) {
        uint8_t len = extractModeName(id, JSON_palette_names, buf, sizeof(buf) - 1);
        if (!len) continue;
        if (id == 0 || buf[0] == '*') { palList.push_back(id); continue; }  // Default + dynamic palettes first
        Named n; n.id = id; strlcpy(n.name, buf, sizeof(n.name)); tmp.push_back(n);
      }
      std::sort(tmp.begin(), tmp.end(), byName);
      for (auto& n : tmp) palList.push_back(n.id);
    }

    static int indexOf(const std::vector<uint8_t>& v, uint8_t id) {
      for (size_t i = 0; i < v.size(); i++) if (v[i] == id) return (int)i;
      return 0;
    }

    const std::vector<uint8_t>* listFor(Mode m) const {
      return m == M_FX ? &fxList : (m == M_PAL ? &palList : nullptr);
    }

    // ---- value <-> knob position ----
    int16_t currentPm(Mode m) {
      Segment& s = seg();
      switch (m) {
        case M_BRI: return clampPm(bri ? ((int)bri - 1) * 1000 / 254 : 0);
        case M_SPD: return clampPm((int)s.speed * 1000 / 255);
        case M_INT: return clampPm((int)s.intensity * 1000 / 255);
        default: {
          const auto* l = listFor(m);
          if (!l || l->size() < 2) return 0;
          int idx = indexOf(*l, m == M_FX ? s.mode : s.palette);
          return clampPm(idx * 1000 / (int)(l->size() - 1));
        }
      }
    }

    int listIndexFromPm(Mode m, int16_t pm) const {
      const auto* l = listFor(m);
      if (!l || l->empty()) return 0;
      return ((int)pm * (int)(l->size() - 1) + 500) / 1000;
    }

    void applyNow(Mode m, int16_t pm) {
      switch (m) {
        case M_BRI: {
          bri = 1 + ((int)pm * 254 + 500) / 1000;
          break;
        }
        case M_SPD: {
          uint8_t v = ((int)pm * 255 + 500) / 1000;
          forSegments([v](Segment& s) { s.speed = v; });
          break;
        }
        case M_INT: {
          uint8_t v = ((int)pm * 255 + 500) / 1000;
          forSegments([v](Segment& s) { s.intensity = v; });
          break;
        }
        case M_FX: {
          if (fxList.empty()) return;
          uint8_t id = fxList[listIndexFromPm(m, pm)];
          forSegments([id](Segment& s) { s.setMode(id); });
          break;
        }
        case M_PAL: {
          if (palList.empty()) return;
          uint8_t id = palList[listIndexFromPm(m, pm)];
          forSegments([id](Segment& s) { s.setPalette(id); });
          break;
        }
        default: return;
      }
      lastSetPm = currentPm(m);
      lastApply = millis();
      announce();
    }

    void setMode(Mode m) {
      mode = m;
      captured = false;
      pendingIdx = -1;
      lastSetPm = -1;
      prevKnobPm = knobPm;
      touch();
    }

    // ---- potentiometer ----
    void readPot() {
      if (!potOk) return;
      uint32_t sum = 0;
      for (int i = 0; i < 8; i++) sum += analogRead(potPin);
      float raw = sum / 8.0f;
      filt = (filt < 0) ? raw : filt + 0.25f * (raw - filt);
      int span = (int)rawMax - (int)rawMin;
      if (span < 100) span = 100;
      int16_t pm = clampPm((int)((filt - rawMin) * 1000.0f / span + 0.5f));
      if (abs(pm - knobPm) < deadband && pm != 0 && pm != 1000) return;  // still within the noise band
      if (pm == knobPm) return;
      prevKnobPm = knobPm;
      knobPm = pm;
      lastKnobMove = millis();
      onKnobMoved();
    }

    void onKnobMoved() {
      if (wake()) { captured = false; return; }
      touch();
      int16_t cur = currentPm(mode);

      if (!captured) {
        bool near    = abs(knobPm - cur) <= 25;
        bool crossed = (prevKnobPm - cur) * (knobPm - cur) <= 0;
        if (!(near || crossed)) return;  // keep showing "turn to grab"
        captured = true;
      }
      if (mode == M_FX || mode == M_PAL) {
        int idx = listIndexFromPm(mode, knobPm);
        const auto* l = listFor(mode);
        int curIdx = l ? indexOf(*l, mode == M_FX ? seg().mode : seg().palette) : 0;
        pendingIdx = (idx == curIdx) ? -1 : idx;  // applied once the knob settles
      } else if (millis() - lastApply >= 40) {
        applyNow(mode, knobPm);
      } else {
        pendingIdx = 1;  // flush the last brightness/speed/intensity step shortly
      }
    }

    void flushPending() {
      if (pendingIdx < 0) return;
      uint32_t now = millis();
      if (mode == M_FX || mode == M_PAL) {
        if (now - lastKnobMove < 350) return;
      } else if (now - lastApply < 40) {
        return;
      }
      pendingIdx = -1;
      applyNow(mode, knobPm);
    }

    // The value can change from the app, a preset or a sync while we hold it: let go, so the
    // knob doesn't fight it, and require a fresh takeover.
    void checkOutsideChange() {
      if (!captured || lastSetPm < 0 || pendingIdx >= 0) return;
      if (abs(currentPm(mode) - lastSetPm) > 12) { captured = false; lastSetPm = -1; needRedraw = true; }
    }

    // ---- display ----
    void initDisplay() {
      if (i2c_sda < 0 || i2c_scl < 0) { DEBUG_PRINTLN(F("cube_ui: no global I2C pins set")); return; }
      if (displayType == 1) u8g2 = new U8G2_SH1106_128X64_NONAME_F_HW_I2C(flip ? U8G2_R2 : U8G2_R0, U8X8_PIN_NONE);
      else                  u8g2 = new U8G2_SSD1306_128X64_NONAME_F_HW_I2C(flip ? U8G2_R2 : U8G2_R0, U8X8_PIN_NONE);
      if (!u8g2) return;
      u8g2->setI2CAddress(i2cAddress << 1);
      u8g2->setBusClock(400000);
      u8g2->begin();
      u8g2->setContrast(contrast);
      u8g2->setFontPosTop();
      asleep = false;
      needRedraw = true;
    }

    static const char* modeLabel(Mode m) {
      switch (m) {
        case M_BRI: return "BRI";
        case M_FX:  return "FX";
        case M_PAL: return "PAL";
        case M_SPD: return "SPD";
        default:    return "INT";
      }
    }

    static const char* modeTitle(Mode m) {
      switch (m) {
        case M_BRI: return "Brightness";
        case M_FX:  return "Effect";
        case M_PAL: return "Palette";
        case M_SPD: return "Speed";
        default:    return "Intensity";
      }
    }

    void drawTabs() {
      u8g2->setFont(u8g2_font_5x7_tr);
      for (int i = 0; i < M_COUNT; i++) {
        int x = i * 26;
        if (i == mode) {
          u8g2->drawBox(x, 0, 25, 9);
          u8g2->setDrawColor(0);
          u8g2->drawStr(x + 13 - u8g2->getStrWidth(modeLabel((Mode)i)) / 2, 1, modeLabel((Mode)i));
          u8g2->setDrawColor(1);
        } else {
          u8g2->drawStr(x + 13 - u8g2->getStrWidth(modeLabel((Mode)i)) / 2, 1, modeLabel((Mode)i));
        }
      }
    }

    // Bar for the value, with a small triangle for the knob when it doesn't hold the value yet.
    void drawBar(int16_t valuePm, int y) {
      u8g2->drawFrame(0, y, 128, 7);
      u8g2->drawBox(1, y + 1, (126 * valuePm) / 1000, 5);
      if (!captured) {
        int kx = 1 + (126 * knobPm) / 1000;
        u8g2->drawTriangle(kx - 3, y + 11, kx + 3, y + 11, kx, y + 8);
      }
    }

    void drawName(const char* name) {
      u8g2->setFont(u8g2_font_helvB10_tr);
      if (u8g2->getStrWidth(name) > 128) u8g2->setFont(u8g2_font_6x10_tr);
      u8g2->drawStr(0, 23, name);
    }

    void drawStatus() {
      u8g2->setFont(u8g2_font_5x7_tr);
      u8g2->drawStr(0, 57, bri ? "ON" : "OFF");

      char ip[20];
      if (apActive && !WLED_CONNECTED) strlcpy(ip, "AP 4.3.2.1", sizeof(ip));
      else if (WLED_CONNECTED) { IPAddress a = Network.localIP(); snprintf(ip, sizeof(ip), "%u.%u", a[2], a[3]); }
      else strlcpy(ip, "no wifi", sizeof(ip));
      u8g2->drawStr(128 - u8g2->getStrWidth(ip), 57, ip);

      if (showAudio) {
        um_data_t* um = nullptr;
        if (UsermodManager::getUMData(&um, USERMOD_ID_AUDIOREACTIVE) && um && um->u_data && um->u_data[2]) {
          uint8_t* fft = (uint8_t*)um->u_data[2];
          for (int i = 0; i < 16; i++) {
            int h = fft[i] / 37;  // 0..6 px
            if (h) u8g2->drawBox(30 + i * 3, 63 - h, 2, h);
          }
        }
      }
    }

    void draw() {
      if (!u8g2 || asleep) return;
      u8g2->clearBuffer();
      if (!bri) {
        u8g2->setFont(u8g2_font_helvB12_tr);
        u8g2->drawStr(64 - u8g2->getStrWidth("OFF") / 2, 18, "OFF");
        u8g2->setFont(u8g2_font_5x7_tr);
        const char* hint = "hold button to turn on";
        u8g2->drawStr(64 - u8g2->getStrWidth(hint) / 2, 40, hint);
        drawStatus();
        u8g2->sendBuffer();
        return;
      }

      drawTabs();
      u8g2->setFont(u8g2_font_5x7_tr);
      u8g2->drawStr(0, 12, modeTitle(mode));
      int16_t cur = currentPm(mode);
      char buf[40];

      if (mode == M_FX || mode == M_PAL) {
        const auto* l = listFor(mode);
        int idx = (pendingIdx >= 0) ? pendingIdx : (l ? indexOf(*l, mode == M_FX ? seg().mode : seg().palette) : 0);
        uint8_t id = (l && !l->empty()) ? (*l)[idx] : 0;
        extractModeName(id, mode == M_FX ? JSON_mode_names : JSON_palette_names, buf, sizeof(buf) - 1);
        drawName(buf);
        char pos[16];
        snprintf(pos, sizeof(pos), "%d/%u%s", idx + 1, l ? (unsigned)l->size() : 0, pendingIdx >= 0 ? " ..." : "");
        u8g2->setFont(u8g2_font_5x7_tr);
        u8g2->drawStr(128 - u8g2->getStrWidth(pos), 12, pos);
        drawBar(pendingIdx >= 0 ? knobPm : cur, 38);
      } else {
        int pct = (cur + 5) / 10;
        snprintf(buf, sizeof(buf), "%d", pct);
        u8g2->setFont(u8g2_font_logisoso18_tn);
        u8g2->drawStr(0, 19, buf);
        int w = u8g2->getStrWidth(buf);
        u8g2->setFont(u8g2_font_6x10_tr);
        u8g2->drawStr(w + 2, 27, "%");
        drawBar(cur, 40);
      }
      if (!captured) {
        u8g2->setFont(u8g2_font_5x7_tr);
        const char* hint = (knobPm < cur) ? "turn knob up to grab" : "turn knob down to grab";
        u8g2->drawStr(128 - u8g2->getStrWidth(hint), 30, hint);
      }
      drawStatus();
      u8g2->sendBuffer();
    }

  public:
    void setup() override {
      buildLists();
      if (enabled && potPin >= 0) {
        // ADC2 is unusable while Wi-Fi is on, so only ADC1 pins (32..39) work.
        if (potPin >= 32 && potPin <= 39 && PinManager::allocatePin(potPin, false, PinOwner::UM_Unspecified)) {
          pinMode(potPin, INPUT);
          analogSetPinAttenuation(potPin, ADC_11db);
          potOk = true;
          readPot();
          prevKnobPm = knobPm;
        } else {
          DEBUG_PRINTLN(F("cube_ui: pot pin must be a free ADC1 pin (32..39)"));
        }
      }
      if (enabled) initDisplay();
      lastActivity = millis();
      initDone = true;
    }

    void loop() override {
      if (!enabled || !initDone) return;
      uint32_t now = millis();
      if (strip.isUpdating() && now - lastDraw < 50) return;

      if (now - lastPotRead >= 20) { lastPotRead = now; readPot(); }
      flushPending();
      checkOutsideChange();

      if (u8g2 && !asleep && sleepSeconds && now - lastActivity > sleepSeconds * 1000UL) {
        asleep = true;
        u8g2->setPowerSave(1);
        return;
      }
      uint32_t refresh = showAudio ? 200 : 1000;
      if (u8g2 && !asleep && (needRedraw || now - lastDraw >= refresh)) {
        needRedraw = false;
        lastDraw = now;
        draw();
      }
    }

    bool handleButton(uint8_t b) override {
      if (!enabled || !initDone || b != buttonIndex) return false;
      bool pressed = isButtonPressed(b);
      uint32_t now = millis();
      if (pressed && !btnDown) {
        btnDown = true; longFired = false; btnDownAt = now;
      } else if (pressed && btnDown && !longFired && now - btnDownAt > 700) {
        longFired = true;
        if (!wake()) { toggleOnOff(); announce(); }
        touch();
      } else if (!pressed && btnDown) {
        btnDown = false;
        if (!longFired && now - btnDownAt > 30) {
          if (!wake()) setMode((Mode)((mode + 1) % M_COUNT));
        }
      }
      return true;  // WLED's own short/long/double press actions are replaced by ours
    }

    void onStateChange(uint8_t callMode) override {
      if (callMode != CALL_MODE_BUTTON) needRedraw = true;
    }

    void addToJsonInfo(JsonObject& root) override {
      if (!enabled) return;
      JsonObject user = root["u"];
      if (user.isNull()) user = root.createNestedObject("u");
      JsonArray a = user.createNestedArray(F("Cube UI"));
      char buf[48];
      snprintf(buf, sizeof(buf), "%s, knob %d%% (raw %d)%s", modeTitle(mode), (knobPm + 5) / 10,
               potOk ? (int)filt : -1, captured ? "" : ", free");
      a.add(buf);
    }

    void addToConfig(JsonObject& root) override {
      JsonObject top = root.createNestedObject(FPSTR(_name));
      top[F("enabled")]        = enabled;
      top[F("pin")]            = potPin;
      top[F("button")]         = buttonIndex;
      top[F("display-type")]   = displayType;
      top[F("i2c-address")]    = i2cAddress;
      top[F("flip")]           = flip;
      top[F("contrast")]       = contrast;
      top[F("sleep-s")]        = sleepSeconds;
      top[F("knob-raw-min")]   = rawMin;
      top[F("knob-raw-max")]   = rawMax;
      top[F("deadband-pm")]    = deadband;
      top[F("apply-to-all")]   = applyToAll;
      top[F("audio-spectrum")] = showAudio;
    }

    bool readFromConfig(JsonObject& root) override {
      JsonObject top = root[FPSTR(_name)];
      bool complete = !top.isNull();
      complete &= getJsonValue(top[F("enabled")],        enabled);
      complete &= getJsonValue(top[F("pin")],            potPin);
      complete &= getJsonValue(top[F("button")],         buttonIndex);
      complete &= getJsonValue(top[F("display-type")],   displayType);
      complete &= getJsonValue(top[F("i2c-address")],    i2cAddress);
      complete &= getJsonValue(top[F("flip")],           flip);
      complete &= getJsonValue(top[F("contrast")],       contrast);
      complete &= getJsonValue(top[F("sleep-s")],        sleepSeconds);
      complete &= getJsonValue(top[F("knob-raw-min")],   rawMin);
      complete &= getJsonValue(top[F("knob-raw-max")],   rawMax);
      complete &= getJsonValue(top[F("deadband-pm")],    deadband);
      complete &= getJsonValue(top[F("apply-to-all")],   applyToAll);
      complete &= getJsonValue(top[F("audio-spectrum")], showAudio);
      if (initDone && u8g2) {  // settings saved at runtime: apply what can be applied live
        u8g2->setContrast(contrast);
        u8g2->setFlipMode(flip ? 1 : 0);
        needRedraw = true;
      }
      return complete;
    }

    void appendConfigData(Print& s) override {
      s.print(F("dd=addDropdown('CubeUI','display-type');"));
      s.print(F("addOption(dd,'SSD1306 128x64 (0.96 in)',0);"));
      s.print(F("addOption(dd,'SH1106 128x64 (1.3 in)',1);"));
      s.print(F("addInfo('CubeUI:pin',1,'potentiometer wiper, ADC1 only (32-39)');"));
      s.print(F("addInfo('CubeUI:button',1,'WLED button index (LED Preferences)');"));
      s.print(F("addInfo('CubeUI:i2c-address',1,'60 = 0x3C, 61 = 0x3D');"));
      s.print(F("addInfo('CubeUI:sleep-s',1,'0 = never');"));
      s.print(F("addInfo('CubeUI:knob-raw-min',1,'see Info page while turning');"));
    }

    uint16_t getId() override { return USERMOD_ID_UNSPECIFIED; }
};

const char CubeUiUsermod::_name[] PROGMEM = "CubeUI";

static CubeUiUsermod cube_ui;
REGISTER_USERMOD(cube_ui);

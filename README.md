# GreenEdge FYP — Fuzzy PWM Control Edition

**Project:** Decentralized Autonomous Greenhouse Using Edge–Cloud Collaboration  
**Dashboard:** Original command-centre / digital-twin Streamlit interface, upgraded from ON/OFF controls to **0–100% proportional PWM duty commands**.

## Run on Windows / Anaconda Prompt

1. Extract the ZIP fully. Open `greenhouse_streamlit_dashboard`.
2. Double-click `START_DASHBOARD.bat`. The launcher attempts to install missing packages into the selected Python interpreter.
3. If the launcher chooses the wrong Python installation, open **Anaconda Prompt**, activate the environment you normally use, navigate to the project directory, and run:

```bat
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

4. Visit `http://localhost:8501` or the URL shown in the terminal. Keep the terminal open.

You can check which interpreter you are using with `where python` and `python -m pip show streamlit`.

## Hardware represented

- Raspberry Pi 5 (intended edge server, **not connected to this simulation**)
- Three ESP32s (intended distributed nodes, **not connected yet**)
- DHT22 (temperature + humidity), soil-moisture sensor, ultrasonic tank-level sensor
- DC water pump, **two independently controlled fans**, full-spectrum grow LED
- **No CO₂ sensor, solenoid valve, or water-flow sensor**
- **No ambient light sensor**: the simulated LED demand is a photoperiod / schedule *request*, **not a measured lux value**.

## What changed in this version

The same original layout, tabs, digital-twin illustration and ultrasonic tank simulator are preserved. **CO₂ remains removed.** The Control page and the Overview add a separate **live Fuzzy PWM Outputs chart**.

| Actuator | Control input | AUTO output | MANUAL control |
|---|---|---|---|
| Pump | Soil moisture + ultrasonic tank fill | ON/OFF with hysteresis (starts below 40% soil; stops at 55% soil) | ON/OFF toggle, **low-water interlock always applies** |
| Fan 1 | DHT22 temperature + humidity | Sugeno fuzzy PWM, 0–100% (temperature-dominant) | 0–100% slider |
| Fan 2 | DHT22 temperature + humidity | Sugeno fuzzy PWM, 0–100% (humidity-responsive) | 0–100% slider |
| Full-spectrum LED | Lighting request (simulated schedule) + DHT22 temperature | Sugeno fuzzy PWM, 0–100% (hot conditions reduce LED drive) | 0–100% slider |

**Note:** The numbers are **PWM duty commands**, not a continuous voltage from an ESP32 DAC. Actual voltage/current and fan speed depend on your drivers and loads. The current software **does not send hardware control signals**.

### Zero-order Sugeno fuzzy logic

`fuzzy_controller.py` contains the complete implemented membership functions, inference engine, and rule tables, with no extra fuzzy libraries required.

- Temperature membership groups: **cool / warm / hot**.
- Humidity groups: **dry / normal / humid**.
- Lighting demand groups: **off / low / medium / high**.
- Rule activation = product of the memberships; output = weighted average of rule singleton values.
- Fan 1 and Fan 2 use separate 3×3 tables. LED uses a 4×3 table.
- Example results:
  - 18°C, 40% RH, 0% lighting request → fan1=0%, fan2=0%, LED=0%.
  - 27.5°C, 67% RH, 80% lighting request → fan1≈38%, fan2≈35%, LED≈80%.
  - 35°C, 90% RH, 100% lighting request → fan1=100%, fan2=100%, LED≈55%.

These membership thresholds and rules are **demonstration values**, not an agronomic specification or validated performance guarantee. Tune them for your plant, enclosure, motor specifications and operating environment.

## Test the dashboard interactively

1. Select **Normal Conditions**, `AUTO`, and turn on **Live telemetry simulation**. The fan duty changes with temperature and humidity.
2. Select **Heat Stress**. Watch both fan PWM percentages increase; LED brightness can decrease as the greenhouse heats up.
3. Move **Lighting request (%) · demo schedule** in the sidebar from 0 to 100. The LED PWM changes. It is a simulated lighting schedule request, not a light-sensor measurement.
4. Select **Dry Soil**. The pump starts, then moisture rises with the illustrative plant dynamics. Pump hysteresis turns it off near 55% soil.
5. Select **Tank Nearly Empty**. The pump stays OFF (critical level ≤15%), including MANUAL mode.
6. Select **MANUAL** to see three independent PWM sliders (fan1, fan2, LED). Return to AUTO to let fuzzy logic compute outputs.
7. Open **Trends** or **Data Log** to view/download the separate Fan 1 PWM (%), Fan 2 PWM (%), Grow LED PWM (%) and Lighting Request (%) columns.

The simplified plant simulation alters temperature, humidity and soil moisture as actuators respond. This is intentionally **illustrative**, not experimentally calibrated. Do not present its trends as actual measured performance.

## Tank distance calibration

For a top-mounted ultrasonic sensor:

```
Tank level (%) = 100 × (empty_distance_cm − measured_distance_cm)
                     / (empty_distance_cm − full_distance_cm)
```

`TANK` in `app.py` uses demo values of **4 cm** full, **30 cm** empty. Low alarm is **25%**; pump cutoff is **15%**. **Measure and calibrate your own reservoir** before hardware tests. The pump interlock also needs a timeout and a stale-sensor fail-safe in real ESP32 firmware.

## Electrical integration notes

- ESP32 logic pins are **3.3 V**, not high-power motor/LED outputs. Use properly rated motor drivers or MOSFET circuits for fan loads, a correct dimmable LED driver for the grow light, and a flyback/protective circuit where applicable.
- Two-wire DC fans may not accept arbitrary PWM in their supply path. Test fan startup and compatible PWM frequency; 4-wire PWM fans require the appropriate control interface. A commanded 15% duty does **not** guarantee 15% actual RPM.
- A full-spectrum LED board may require **constant-current regulation**. Do not connect it directly to an ESP32 or PWM raw mains without a rated driver.
- The Raspberry Pi 5 and ESP32s need proper power supplies, common reference where appropriate, electrical isolation when necessary, and independent protective devices.
- Example real architecture: Raspberry Pi 5 runs MQTT/fuzzy optimization; ESP32 #1 manages pump + soil; ESP32 #2 drives both fans + LED; ESP32 #3 monitors water level and publishes a pump inhibit. Implement a *local safe fallback* on ESP32 when Pi/MQTT messages stop.
- `app.py` currently uses no MQTT connection and cannot directly control physical hardware. Integration requires MQTT topics, input validation, command expiry, firmware PWM (e.g. ESP32 LEDC), and safety handling.

## Project files

- `app.py` — modified Streamlit dashboard, interactive plant simulator, charting and control UI
- `fuzzy_controller.py` — self-contained Sugeno fuzzy control algorithm
- `tests/test_fuzzy_controller.py` — unit tests for rule outputs and safe ranges
- `assets/greenhouse_digital_twin.png` — original digital-twin artwork
- `requirements.txt`, `.streamlit/config.toml`, `START_DASHBOARD.bat` — installation and launch configuration

To run the automated fuzzy tests without starting Streamlit:

```bat
python -m unittest discover -s tests -v
```

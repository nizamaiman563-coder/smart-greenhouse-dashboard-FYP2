"""Transparent zero-order Sugeno fuzzy controllers for a greenhouse demo.

Fan 1: temperature-dominant ventilation; fan 2: humidity-responsive exhaust.
Grow LED: commanded lighting demand (e.g. from photoperiod schedule) and
           greenhouse temperature (thermal derating).  No light sensor assumed.
All outputs represent 0..100 percent PWM *duty requests*, not analog voltage.
"""
from __future__ import annotations


def bound(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def triangle(x: float, left: float, centre: float, right: float) -> float:
    if not left < centre < right:
        raise ValueError("Triangular membership parameters must increase")
    if x <= left or x >= right:
        return 0.0
    if x == centre:
        return 1.0
    if x < centre:
        return (x - left) / (centre - left)
    return (right - x) / (right - centre)


def left_shoulder(x: float, full_below: float, zero_above: float) -> float:
    if x <= full_below:
        return 1.0
    if x >= zero_above:
        return 0.0
    return (zero_above - x) / (zero_above - full_below)


def right_shoulder(x: float, zero_below: float, full_above: float) -> float:
    if x <= zero_below:
        return 0.0
    if x >= full_above:
        return 1.0
    return (x - zero_below) / (full_above - zero_below)


def temp_memberships(temp_c: float) -> dict[str, float]:
    return {
        "cool": left_shoulder(temp_c, 21.0, 26.0),
        "warm": triangle(temp_c, 22.0, 27.5, 33.0),
        "hot": right_shoulder(temp_c, 29.0, 35.0),
    }


def humidity_memberships(rh: float) -> dict[str, float]:
    return {
        "dry": left_shoulder(rh, 45.0, 60.0),
        "normal": triangle(rh, 50.0, 67.5, 85.0),
        "humid": right_shoulder(rh, 75.0, 90.0),
    }


def demand_memberships(demand: float) -> dict[str, float]:
    d = bound(demand)
    return {
        "off": left_shoulder(d, 0.0, 20.0),
        "low": triangle(d, 0.0, 28.0, 56.0),
        "medium": triangle(d, 34.0, 60.0, 86.0),
        "high": right_shoulder(d, 68.0, 94.0),
    }


def _infer(a: dict[str, float], b: dict[str, float], rules: dict[tuple[str, str], float]) -> float:
    # Product inference and weighted-average singleton defuzzification.
    weight_sum = 0.0
    total = 0.0
    for (a_name, b_name), crisp_output in rules.items():
        firing = a[a_name] * b[b_name]
        weight_sum += firing
        total += firing * crisp_output
    return bound(total / weight_sum) if weight_sum else 0.0


# Each row is temperature COOL/WARM/HOT and each column DRY/NORMAL/HUMID.
# Tune on a real prototype; these are illustrative FYP starting rules.
FAN_1_RULES = {
    ("cool", "dry"): 0,   ("cool", "normal"): 10, ("cool", "humid"): 40,
    ("warm", "dry"): 22,  ("warm", "normal"): 38, ("warm", "humid"): 72,
    ("hot", "dry"): 77,   ("hot", "normal"): 87,  ("hot", "humid"): 100,
}
FAN_2_RULES = {
    ("cool", "dry"): 0,   ("cool", "normal"): 10, ("cool", "humid"): 55,
    ("warm", "dry"): 15,  ("warm", "normal"): 35, ("warm", "humid"): 82,
    ("hot", "dry"): 68,   ("hot", "normal"): 84,  ("hot", "humid"): 100,
}

# LED demand comes from a user/programmed schedule, NOT a nonexistent LDR.
# A hot greenhouse derates brightness to reduce additional heat input.
LED_RULES = {
    ("off", "cool"): 0,      ("off", "warm"): 0,       ("off", "hot"): 0,
    ("low", "cool"): 27,     ("low", "warm"): 22,      ("low", "hot"): 12,
    ("medium", "cool"): 62,  ("medium", "warm"): 56,   ("medium", "hot"): 32,
    ("high", "cool"): 100,   ("high", "warm"): 92,     ("high", "hot"): 55,
}


def fuzzy_outputs(temp_c: float, humidity_pct: float, lighting_request_pct: float) -> dict[str, float]:
    """Return independent fan and LED PWM duty requests (0..100%)."""
    t = temp_memberships(float(temp_c))
    h = humidity_memberships(bound(humidity_pct))
    d = demand_memberships(lighting_request_pct)
    # For LED inference first axis is lighting demand; second is temperature.
    fan1 = _infer(t, h, FAN_1_RULES)
    fan2 = _infer(t, h, FAN_2_RULES)
    led = _infer(d, t, LED_RULES)
    # Explicit all-off at a zero lighting request, and safety heat cutoff
    # only for LED; ventilation stays free to respond to heat.
    if lighting_request_pct <= 0:
        led = 0.0
    return {"fan1_pct": round(fan1, 1), "fan2_pct": round(fan2, 1), "led_pct": round(led, 1)}

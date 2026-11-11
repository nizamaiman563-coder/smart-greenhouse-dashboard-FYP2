import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fuzzy_controller import fuzzy_outputs, temp_memberships, humidity_memberships, demand_memberships


class FuzzyControllerTests(unittest.TestCase):
    def test_minimum_and_maximum_duty(self):
        self.assertEqual(fuzzy_outputs(18, 40, 0), {'fan1_pct': 0.0, 'fan2_pct': 0.0, 'led_pct': 0.0})
        self.assertEqual(fuzzy_outputs(35, 90, 100), {'fan1_pct': 100.0, 'fan2_pct': 100.0, 'led_pct': 55.0})

    def test_nominal_values(self):
        self.assertEqual(fuzzy_outputs(27.5, 67, 80), {'fan1_pct': 38.0, 'fan2_pct': 35.0, 'led_pct': 80.0})

    def test_zero_schedule_always_off(self):
        for temp in range(12, 46, 2):
            self.assertEqual(fuzzy_outputs(temp, 75, 0)['led_pct'], 0.0)

    def test_all_outputs_in_limits(self):
        for t in range(12, 46, 2):
            for humidity in range(0, 101, 10):
                for demand in range(0, 101, 10):
                    outputs = fuzzy_outputs(t, humidity, demand)
                    self.assertTrue(all(0 <= val <= 100 for val in outputs.values()))

    def test_coverage_of_input_space(self):
        for t in [0, 20, 25, 30, 34, 50]:
            self.assertGreater(sum(temp_memberships(t).values()), 0)
        for h in [0, 45, 60, 75, 85, 100]:
            self.assertGreater(sum(humidity_memberships(h).values()), 0)
        for d in [0, 15, 29, 48, 70, 100]:
            self.assertGreater(sum(demand_memberships(d).values()), 0)

    def test_temperature_raise_increases_fan(self):
        cool = fuzzy_outputs(22, 65, 75)
        hot = fuzzy_outputs(35, 65, 75)
        self.assertGreater(hot['fan1_pct'], cool['fan1_pct'])
        self.assertGreater(hot['fan2_pct'], cool['fan2_pct'])
        self.assertLess(hot['led_pct'], cool['led_pct'])

    def test_humidity_raise_increases_exhaust(self):
        dry = fuzzy_outputs(28, 45, 75)
        wet = fuzzy_outputs(28, 95, 75)
        self.assertGreater(wet['fan2_pct'], dry['fan2_pct'])

    def test_lighting_demand_increases_output(self):
        low = fuzzy_outputs(27, 65, 20)['led_pct']
        high = fuzzy_outputs(27, 65, 90)['led_pct']
        self.assertGreater(high, low)

if __name__ == '__main__':
    unittest.main()

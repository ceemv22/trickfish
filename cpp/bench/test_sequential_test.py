from fractions import Fraction
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sequential_test import assess_signs, probability, validate_parameters


PARAMETERS = {"p0": "0.25", "p1": "0.75", "alpha": "0.25", "beta": "0.25", "max_pairs": 32}


class SequentialArithmeticTests(unittest.TestCase):
    def test_exact_first_crossing_and_no_continuation_after_stop(self):
        self.assertEqual(assess_signs([1], PARAMETERS)["decision"], "continue")
        self.assertEqual(assess_signs([1, 1], PARAMETERS)["decision"], "accept_h1")
        self.assertEqual(assess_signs([-1, -1], PARAMETERS)["decision"], "accept_h0")
        for signs in ([1, 1, -1], [-1, -1, 0], [None, 1]):
            with self.assertRaises(ValueError): assess_signs(signs, PARAMETERS)
        equality = {**PARAMETERS, "p0": "0.2", "p1": "0.8"}
        self.assertEqual(assess_signs([1], equality)["decision"], "accept_h1")
        self.assertEqual(assess_signs([-1], equality)["decision"], "accept_h0")

    def test_exhaustive_stopped_path_error_mass_respects_conservative_bounds(self):
        pending = [(Fraction(1), Fraction(1), [])]
        false_positive = false_negative = Fraction(0)
        p0, p1 = Fraction(1, 4), Fraction(3, 4)
        for _ in range(8):
            next_paths = []
            for null_mass, alternative_mass, signs in pending:
                for sign in (-1, 1):
                    mass0 = null_mass * (p0 if sign == 1 else 1 - p0)
                    mass1 = alternative_mass * (p1 if sign == 1 else 1 - p1)
                    result = assess_signs(signs + [sign], PARAMETERS)
                    if result["decision"] == "accept_h1": false_positive += mass0
                    elif result["decision"] == "accept_h0": false_negative += mass1
                    else: next_paths.append((mass0, mass1, signs + [sign]))
            pending = next_paths
        self.assertLessEqual(false_positive, Fraction(1, 4))
        self.assertLessEqual(false_negative, Fraction(1, 4))
        self.assertGreater(false_positive, 0)
        self.assertGreater(false_negative, 0)

    def test_ties_caps_unfinished_and_identical_controls_do_not_fake_acceptance(self):
        capped = {**PARAMETERS, "max_pairs": 3}
        self.assertEqual(assess_signs([0, 0, 0], capped)["decision"], "inconclusive_horizon")
        self.assertEqual(assess_signs([1, 1, 1], capped, identical=True)["decision"], "blocked_identical")
        self.assertEqual(assess_signs([1, None], capped)["decision"], "blocked_unfinished")
        self.assertEqual(assess_signs([1, 0, -1], capped)["decisive_pairs"], 2)
        for signs in ([True], [2], ["1"], [1] * 33):
            with self.assertRaises(ValueError): assess_signs(signs, PARAMETERS)

    def test_probability_validation_and_extreme_exact_products(self):
        self.assertEqual(probability("0.000000000001"), Fraction(1, 10**12))
        for value in (0.05, "NaN", "1", "0.0", "0.1234567890123", "0.5e-1", True):
            with self.assertRaises(ValueError): probability(value)
        for update in ({"p0": "0.75"}, {"max_pairs": True}, {"alpha": "0.5"}, {"extra": 1}):
            with self.assertRaises(ValueError): validate_parameters({**PARAMETERS, **update})
        extreme = {"p0": "0.000000000001", "p1": "0.999999999999", "alpha": "0.000000000001", "beta": "0.000000000001", "max_pairs": 4096}
        result = assess_signs([1, -1] * 2048, extreme, identical=True)
        self.assertEqual(result["decision"], "blocked_identical")
        self.assertEqual(result["trace"][-1]["log_likelihood_ratio"], 0)


if __name__ == "__main__":
    unittest.main()

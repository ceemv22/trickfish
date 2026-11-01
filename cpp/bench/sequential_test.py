from decimal import Decimal
from fractions import Fraction
import math
import re


def probability(text):
    if not isinstance(text, str) or re.fullmatch(r"0\.[0-9]{1,12}", text) is None:
        raise ValueError("probabilities require decimal strings with 1..12 fractional digits")
    value = Fraction(Decimal(text))
    if not 0 < value < 1: raise ValueError("probabilities must be strictly between zero and one")
    return value


def validate_parameters(parameters):
    if not isinstance(parameters, dict) or set(parameters) != {"p0", "p1", "alpha", "beta", "max_pairs"}:
        raise ValueError("expected exact sequential-test parameter fields")
    p0, p1, alpha, beta = (probability(parameters[name]) for name in ("p0", "p1", "alpha", "beta"))
    if not p0 < p1 or not alpha < Fraction(1, 2) or not beta < Fraction(1, 2):
        raise ValueError("require p0 < p1 and alpha/beta < one half")
    if type(parameters["max_pairs"]) is not int or not 1 <= parameters["max_pairs"] <= 4096:
        raise ValueError("sequential horizon must be 1..4096 color pairs")
    return p0, p1, alpha, beta


def assess_signs(signs, parameters, identical=False):
    p0, p1, alpha, beta = validate_parameters(parameters)
    if not isinstance(signs, list) or len(signs) > parameters["max_pairs"]:
        raise ValueError("sequential observations exceed the fixed maximum horizon")
    ratio = Fraction(1)
    wins = losses = ties = 0
    trace = []
    decision = "continue"
    for pair, sign in enumerate(signs, 1):
        if decision != "continue": raise ValueError("observations continue beyond the first stopping boundary")
        if sign is not None and (type(sign) is not int or sign not in (-1, 0, 1)):
            raise ValueError("pair sign must be -1, 0, 1 or unfinished")
        if sign is None:
            decision = "blocked_unfinished"
        elif sign > 0:
            wins += 1
            ratio *= p1 / p0
        elif sign < 0:
            losses += 1
            ratio *= (1 - p1) / (1 - p0)
        else:
            ties += 1
        if decision == "continue" and not identical:
            if ratio >= 1 / alpha: decision = "accept_h1"
            elif ratio <= beta: decision = "accept_h0"
        trace.append({"pair": pair, "sign": sign, "log_likelihood_ratio": math.log(ratio.numerator) - math.log(ratio.denominator),
            "decision": decision})
    if decision == "continue" and len(signs) == parameters["max_pairs"]:
        decision = "blocked_identical" if identical else "inconclusive_horizon"
    return {"decision": decision, "observed_pairs": len(signs), "wins": wins, "losses": losses, "ties": ties,
        "decisive_pairs": wins + losses, "trace": trace,
        "boundaries": {"upper": "1/alpha", "lower": "beta", "comparison": "exact rational; logarithms are display only"},
        "model": "independent decisive color-pair signs with constant p; tied pairs excluded conditionally",
        "limitations": "not mean-score/Elo evidence; capped inconclusive runs are not acceptances; model, independence and prespecification are not authenticated"}

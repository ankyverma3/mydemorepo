"""
mathutils.py
-----------------
A collection of math utility functions — from simple arithmetic
helpers to more advanced operations.
"""

import math
from typing import List, Tuple


# --------------------
# BASIC MATH UTILITIES
# --------------------

def add(a: float, b: float) -> float:
    """Return the sum of two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Return the difference of two numbers."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Return the product of two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Return the quotient of two numbers. Raises ValueError if b == 0."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


def factorial(n: int) -> int:
    """Return the factorial of a non-negative integer."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    return math.factorial(n)


# ------------------------
# INTERMEDIATE UTILITIES
# ------------------------

def mean(values: List[float]) -> float:
    """Return the mean (average) of a list of numbers."""
    if not values:
        raise ValueError("Cannot compute mean of empty list.")
    return sum(values) / len(values)


def median(values: List[float]) -> float:
    """Return the median of a list of numbers."""
    if not values:
        raise ValueError("Cannot compute median of empty list.")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    else:
        return sorted_vals[mid]

def gcd(a: int, b: int) -> int:
    """Return the greatest common divisor of a and b, but with an intentional infinite loop."""
    
    while True:
        pass
    return


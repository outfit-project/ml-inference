import math


def normalize_func(vector: list[float])->list[float]:
    sum_of_squares = 0.0

    for x in vector:
        sum_of_squares += x**2

    length = math.sqrt(sum_of_squares)
    if length == 0.0:
        return [0.0] * len(vector)

    return [x / length for x in vector]

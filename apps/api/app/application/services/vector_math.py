from math import sqrt


def normalize(vector: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def average(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    size = len(vectors[0])
    summed = [0.0] * size
    for vector in vectors:
        for index, value in enumerate(vector):
            summed[index] += float(value)
    return normalize([value / len(vectors) for value in summed])


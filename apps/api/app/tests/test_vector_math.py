from app.application.services.vector_math import average, normalize


def test_normalize_zero_vector() -> None:
    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_average_vectors_normalizes_result() -> None:
    result = average([[1.0, 0.0], [1.0, 1.0]])

    assert result is not None
    assert result[0] > result[1]
    assert round(sum(value * value for value in result), 2) == 1.0


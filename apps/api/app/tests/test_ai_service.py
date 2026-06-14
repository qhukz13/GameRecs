from app.application.services.ai_service import AIService


def test_review_analysis_extracts_sentiment_and_embedding() -> None:
    service = AIService()

    analysis = service.analyze_review(
        "Great combat and chaos, but not puzzle heavy.", rating=9
    )

    assert analysis.sentiment == "positive"
    assert "combat" in analysis.liked_features
    assert "puzzle" in analysis.disliked_features
    assert len(analysis.embedding) == 8


def test_game_embedding_is_deterministic() -> None:
    service = AIService()

    first = service.embed_game("Portal 2", "Puzzle strategy", ["puzzle"], ["strategy"])
    second = service.embed_game("Portal 2", "Puzzle strategy", ["puzzle"], ["strategy"])

    assert first == second
    assert len(first) == 8


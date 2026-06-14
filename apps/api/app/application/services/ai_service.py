from app.application.services.vector_math import normalize
from app.core.config import settings
from app.domain.entities import ReviewAnalysis
from app.infrastructure.db.models import GameModel


class AIService:
    vocabulary = (
        "strategy",
        "combat",
        "story",
        "puzzle",
        "survival",
        "building",
        "casual",
        "chaos",
        "action",
        "rpg",
        "sandbox",
        "horror",
        "simulation",
        "running",
        "racing",
        "platformer",
        "exploration",
        "crafting",
        "farming",
        "stealth",
        "co-op",
        "cooperative",
        "multiplayer",
        "single-player",
        "indie",
        "anime",
        "pixel",
        "roguelike",
        "turn-based",
        "action-rpg",
        "survival-horror",
        "open-world",
        "tower-defense",
        "card-game",
        "puzzle-platformer",
        "metroidvania",
        "dungeon-crawler",
        "hack and slash",
        "bullet-hell",
        "shoot-em-up",
        "visual-novel",
        "dating-sim",
        "typing",
        "music",
        "rhythm",
        "party game",
        "board game",
        "trivia",
        "quiz",
        "strategy",
        "tactical",
        "wargame",
        "rts",
        "turn-based",
        "real-time",
        "simulation",
        "city-builder",
        "tycoon",
        "management",
        "business",
        "life-sim",
        "sandbox",
        "survival",
        "survival",
        "battle-royale",
        "arena",
        "fps",
        "tps",
        "third-person",
        "first-person",
        "isometric",
        "top-down",
        "side-scroller",
        "2D",
        "3D",
        "2.5D",
        "stylized",
        "realistic",
        "voxel",
        "retro",
        "cinematic",
        "story-rich",
        "narrative",
        "interactive",
        "choice-matters",
        "branching",
        "emergent",
        "procedural",
        "roguelite",
        "roguelike",
        "permadeath",
        "speedrun",
        "competitive",
        "casual",
        "relaxing",
        "cozy",
        "chill",
        "hardcore",
        "intense",
        "horror",
        "comedy",
        "mystery",
        "detective",
        "noir",
        "fantasy",
        "sci-fi",
        "cyberpunk",
        "post-apocalyptic",
        "historical",
        "medieval",
        "space",
        "pirate",
        "ninja",
        "samurai",
        "war",
        "military",
        "police",
        "spy",
        "western",
        "wild-west",
        "asian",
        "chinese",
        "japanese",
        "korean",
        "italian",
        "greek",
        "egyptian",
        "mayan",
        "viking",
        "celtic",
        "slavic",
        "tropical",
        "desert",
        "forest",
        "mountain",
        "ocean",
        "undersea",
        "astro",
        "moon",
        "mars",
        "alien",
        "zombie",
        "vampire",
        "werewolf",
        "ghost",
        "mummy",
        "demon",
        "angel",
        "god",
        "dragon",
        "monster",
        "creature",
        "pet",
        "animal",
        "robot",
        "mech",
        "cyborg",
        "mutant",
        "alien",
        "witch",
        "wizard",
        "mage",
        "knight",
        "paladin",
        "rogue",
        "thief",
        "assassin",
        "archer",
        "warrior",
        "hunter",
        "necromancer",
        "cleric",
        "bard",
        "druid",
        "ranger",
        "warlock",
        "pirate",
        "captain",
        "chef",
        "farmer",
        "builder",
        "miner",
        "blacksmith",
        "alchemist",
        "scientist",
        "pilot",
        "driver",
        "athlete",
        "gamer",
        "streamer",
        "blogger",
        "influencer",
        "developer",
        "programmer",
        "hacker",
        "detective",
        "journalist",
        "reporter",
        "photographer",
        "musician",
        "singer",
        "dancer",
        "actor",
        "actress",
    )

    positive_words = {
        "love",
        "liked",
        "great",
        "fun",
        "excellent",
        "best",
        "enjoyed",
        "люблю",
        "понрав",
        "класс",
        "весело",
        "отлич",
    }
    negative_words = {
        "hate",
        "boring",
        "bad",
        "slow",
        "annoying",
        "frustrating",
        "disliked",
        "скуч",
        "плох",
        "раздраж",
        "медлен",
    }

    def embed_text(self, text: str) -> list[float]:
        dim = settings.embedding_dim
        lower = text.lower()
        vector: list[float] = []
        for term in self.vocabulary[:dim]:
            direct = lower.count(term)
            fuzzy = sum(1 for word in lower.split() if term[:4] in word)
            vector.append(float(direct * 2 + fuzzy))
        if not any(vector):
            for index, char in enumerate(lower.encode("utf-8")):
                vector[index % dim] += (char % 17) / 17
        # Ensure the vector is exactly the right dimension
        while len(vector) < dim:
            vector.append(0.0)
        return normalize(vector[:dim])

    def embed_game(self, title: str, description: str, genres: list[str], tags: list[str]) -> list[float]:
        return self.embed_text(" ".join([title, description, *genres, *tags]))

    def analyze_review(self, review_text: str, rating: int) -> ReviewAnalysis:
        lower = review_text.lower()
        liked = [term for term in self.vocabulary if term in lower]
        disliked = [term for term in self.vocabulary if f"not {term}" in lower or f"no {term}" in lower]

        positive_hits = sum(1 for word in self.positive_words if word in lower)
        negative_hits = sum(1 for word in self.negative_words if word in lower)
        if rating >= 8 or positive_hits > negative_hits:
            sentiment = "positive"
        elif rating <= 4 or negative_hits > positive_hits:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        if sentiment == "positive" and not liked:
            liked = ["cooperative flow"]
        if sentiment == "negative" and not disliked:
            disliked = ["friction"]

        return ReviewAnalysis(
            liked_features=liked,
            disliked_features=disliked,
            sentiment=sentiment,
            embedding=self.embed_text(review_text),
        )

    def explain_recommendation(
        self, game: GameModel, score: float, group_features: list[str] | None = None
    ) -> str:
        features = ", ".join(group_features or game.tags[:3] or game.genres[:3] or ["co-op play"])
        percent = round(score * 100)
        return f"{game.title} matches the group's preference profile around {features}; similarity score {percent}%."


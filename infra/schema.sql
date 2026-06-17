CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE users (
    id uuid PRIMARY KEY,
    email varchar(320) NOT NULL UNIQUE,
    username varchar(80) NOT NULL UNIQUE,
    hashed_password varchar(255) NOT NULL,
    profile_embedding vector(8),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash varchar(128) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE groups (
    id uuid PRIMARY KEY,
    name varchar(120) NOT NULL,
    owner_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    profile_embedding vector(8),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE group_members (
    group_id uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE group_games (
    group_id uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (group_id, game_id)
);

CREATE TABLE games (
    id uuid PRIMARY KEY,
    external_id varchar(120) UNIQUE,
    title varchar(200) NOT NULL,
    description text NOT NULL,
    genres jsonb NOT NULL DEFAULT '[]'::jsonb,
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    players_min integer NOT NULL,
    players_max integer NOT NULL,
    embedding vector(8),
    release_date timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    rating integer NOT NULL CHECK (rating >= 1 AND rating <= 10),
    review_text text NOT NULL,
    liked_features jsonb NOT NULL DEFAULT '[]'::jsonb,
    disliked_features jsonb NOT NULL DEFAULT '[]'::jsonb,
    sentiment varchar(32) NOT NULL DEFAULT 'neutral',
    review_embedding vector(8),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, game_id)
);

CREATE TABLE recommendations (
    id uuid PRIMARY KEY,
    group_id uuid NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    score double precision NOT NULL,
    explanation text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (group_id, game_id)
);

CREATE INDEX ix_games_embedding_cosine
    ON games USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX ix_reviews_user_id ON reviews(user_id);
CREATE INDEX ix_recommendations_group_id ON recommendations(group_id);

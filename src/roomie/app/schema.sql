BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    budget INTEGER CHECK (budget IS NULL OR budget >= 0),
    preferred_location TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_interests (
    profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    interest TEXT NOT NULL,
    PRIMARY KEY (profile_id, interest)
);

CREATE TABLE IF NOT EXISTS connection_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (from_user_id, to_user_id),
    CHECK (from_user_id != to_user_id)
);

CREATE INDEX IF NOT EXISTS idx_profile_interests_interest
    ON profile_interests (interest);

CREATE INDEX IF NOT EXISTS idx_connection_requests_to
    ON connection_requests (to_user_id);

CREATE TABLE IF NOT EXISTS preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    cleanliness TEXT,
    sleep_schedule TEXT,
    study_habits TEXT,
    smoking_preference TEXT,
    pet_preference TEXT,
    budget INTEGER CHECK (
        budget IS NULL OR (typeof(budget) = 'integer' AND budget >= 0)
    )
);

COMMIT;

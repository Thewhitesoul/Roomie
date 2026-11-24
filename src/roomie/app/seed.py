"""Fake demo data: `flask --app app seed` and `flask --app app seed --remove`.

Every fake account uses an @example.com email (a domain reserved for examples),
so fake data is easy to spot and `--remove` deletes only fake accounts.
Running the command again skips fake users that already exist.
"""
import random

import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from .db import get_db
from .frontend import PREFERENCE_FIELDS

FAKE_DOMAIN = "example.com"
DEFAULT_COUNT = 100
DEFAULT_PASSWORD = "password123"

FIRST_NAMES = [
    "Aarav", "Abigail", "Aisha", "Alex", "Amara", "Ananya", "Ava", "Bibek", "Brooke",
    "Caleb", "Camila", "Carlos", "Chloe", "Daniel", "Diya", "Elena", "Ethan", "Fatima",
    "Grace", "Hannah", "Isaac", "Jada", "Jordan", "Kavya", "Liam", "Lucas", "Maya",
    "Mei", "Mohammed", "Nadia", "Noah", "Olivia", "Priya", "Rohan", "Sara", "Sofia",
    "Sujan", "Taylor", "Tyler", "Zoe",
]
LAST_NAMES = [
    "Adhikari", "Brown", "Chen", "Davis", "Garcia", "Gurung", "Johnson", "Khan", "Kim",
    "Lee", "Lopez", "Martinez", "Miller", "Nguyen", "Patel", "Rai", "Shrestha", "Smith",
    "Taylor", "Thapa", "Walker", "Williams", "Wilson", "Young",
]
LOCATIONS = [
    "Topeka, KS", "Topeka, KS", "Topeka, KS",  # most students are near Washburn
    "Lawrence, KS", "Manhattan, KS", "Kansas City, KS", "Wichita, KS",
]
INTERESTS = [
    "basketball", "board games", "cooking", "cycling", "dancing", "fishing", "fitness",
    "gaming", "hiking", "movies", "music", "painting", "photography", "reading",
    "running", "soccer", "studying", "swimming", "travel", "volunteering", "yoga",
]
MAJORS = [
    "computer science", "nursing", "business", "biology", "psychology", "accounting",
    "education", "criminal justice", "art", "kinesiology", "mass media", "engineering",
]
BIO_TEMPLATES = [
    "{major} student who loves {i1} and {i2}. Looking for a respectful roommate.",
    "Hi! I'm studying {major}. Free time goes to {i1}, and I'm always up for {i2}.",
    "Junior in {major}. Quiet on weeknights, social on weekends. Big fan of {i1}.",
    "I study {major} and enjoy {i1}. Hoping to find someone easygoing to share a place with.",
    "{major} major, into {i1} and {i2}. I keep shared spaces tidy and pay rent on time.",
]


def _fake_people(count, seed=2026):
    """Build `count` fake people. A fixed seed gives the same people every run."""
    rng = random.Random(seed)
    people = []
    for n in range(1, count + 1):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        username = f"{first}_{last}{n}".lower()          # n keeps every username unique
        interests = rng.sample(INTERESTS, rng.randint(2, 5))
        budget = rng.randrange(400, 1225, 25)
        people.append({
            "username": username,
            "email": f"{username}@{FAKE_DOMAIN}",
            "name": f"{first} {last}",
            "age": rng.randint(18, 26),
            "housing_status": rng.choice(["needs_housing", "needs_housing", "has_housing"]),
            "budget": budget,
            "preferred_location": rng.choice(LOCATIONS),
            "interests": interests,
            "bio": rng.choice(BIO_TEMPLATES).format(
                major=rng.choice(MAJORS).capitalize(), i1=interests[0], i2=interests[1]),
            # Valid choices come from the same list the preferences form uses.
            "preferences": {
                field: rng.choice(list(spec["choices"])) for field, spec in PREFERENCE_FIELDS.items()
            } | {"budget": budget},
        })
    return people


def seed_fake_data(count=DEFAULT_COUNT, password=DEFAULT_PASSWORD, seed=2026):
    """Add fake users. Returns how many were newly created."""
    db = get_db()
    password_hash = generate_password_hash(password)     # same hash for all, so seeding is fast
    rng = random.Random(seed + 1)
    created = 0

    with db:  # one transaction: all fake data is saved, or none of it
        for person in _fake_people(count, seed):
            exists = db.execute(
                "SELECT 1 FROM users WHERE username = ? OR email = ?",
                (person["username"], person["email"]),
            ).fetchone()
            if exists:
                continue

            user_id = db.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (person["username"], person["email"], password_hash),
            ).lastrowid
            profile_id = db.execute(
                """INSERT INTO profiles
                   (user_id, name, age, housing_status, bio, budget, preferred_location)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, person["name"], person["age"], person["housing_status"],
                 person["bio"], person["budget"], person["preferred_location"]),
            ).lastrowid
            db.executemany(
                "INSERT INTO profile_interests (profile_id, interest) VALUES (?, ?)",
                [(profile_id, i) for i in person["interests"]],
            )
            prefs = person["preferences"]
            db.execute(
                f"INSERT INTO preferences (user_id, {', '.join(prefs)}) "
                f"VALUES (?, {', '.join('?' for _ in prefs)})",
                (user_id, *prefs.values()),
            )
            created += 1

        # Some interest between fake users, so match lists aren't empty in the demo.
        fake_ids = [r["id"] for r in db.execute(
            "SELECT id FROM users WHERE email LIKE ? ORDER BY id", (f"%@{FAKE_DOMAIN}",))]
        if len(fake_ids) >= 2:
            pairs = set()
            for _ in range(len(fake_ids) * 3 // 2):          # about 1.5 interests per user
                a, b = rng.sample(fake_ids, 2)
                pairs.add((a, b))
                if rng.random() < 0.2:                       # about 1 in 5 become mutual
                    pairs.add((b, a))
            db.executemany(
                "INSERT OR IGNORE INTO connection_requests (from_user_id, to_user_id) VALUES (?, ?)",
                sorted(pairs),
            )
    return created


def remove_fake_data():
    """Delete every @example.com account. Profiles, interests, preferences and
    connection requests go with them (ON DELETE CASCADE). Real accounts are untouched."""
    db = get_db()
    with db:
        cur = db.execute("DELETE FROM users WHERE email LIKE ?", (f"%@{FAKE_DOMAIN}",))
    return cur.rowcount


@click.command("seed")
@click.option("--count", default=DEFAULT_COUNT, show_default=True, help="How many fake users.")
@click.option("--password", default=DEFAULT_PASSWORD, show_default=True,
              help="Password for every fake account.")
@click.option("--remove", is_flag=True, help="Delete all fake (@example.com) accounts instead.")
@with_appcontext
def seed_command(count, password, remove):
    """Add fake demo users, or remove them with --remove."""
    if remove:
        click.echo(f"Removed {remove_fake_data()} fake users.")
        return
    created = seed_fake_data(count, password)
    total = get_db().execute(
        "SELECT COUNT(*) FROM users WHERE email LIKE ?", (f"%@{FAKE_DOMAIN}",)).fetchone()[0]
    click.echo(f"Added {created} fake users ({total} fake users in total). "
               f"Every fake account's password is: {password}")


def init_app(app):
    app.cli.add_command(seed_command)

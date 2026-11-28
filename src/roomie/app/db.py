import sqlite3
import click
from flask import current_app,  g
from flask.cli import with_appcontext

SQLITE_MAX_INTEGER = 9223372036854775807

def get_db():
    if "db" not in g:
        g.db=sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory=sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
        try:
            migrate_profiles(g.db)
        except Exception:
            g.db.close()
            g.pop("db", None)
            raise
    return g.db
# Fixed, additive definitions: never copy/rebuild/drop a table or alter IDs.
PROFILE_ADDITIONS = {
    "age": "INTEGER CHECK (age IS NULL OR (typeof(age) = 'integer' AND age BETWEEN 18 AND 120))",
    "housing_status": "TEXT CHECK (housing_status IS NULL OR housing_status IN ('needs_housing', 'has_housing'))",
}


def migrate_profiles(connection):
    columns = {row[1] for row in connection.execute("PRAGMA table_info(profiles)")}
    if not columns or all(name in columns for name in PROFILE_ADDITIONS):
        return
    # Recheck under the write lock so simultaneous workers cannot add twice.
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(profiles)")}
        for name, definition in PROFILE_ADDITIONS.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE profiles ADD COLUMN {name} {definition}")


@click.command("migrate-db")
@with_appcontext
def migrate_db_command():
    """Add profile onboarding columns without deleting existing data."""
    import os
    if not os.path.isfile(current_app.config["DATABASE"]):
        raise click.ClickException("Database not found. Run init-db for a new database.")
    connection = get_db()  # Also migrates automatically on first DB use.
    if not connection.execute("PRAGMA table_info(profiles)").fetchall():
        raise click.ClickException("Profiles table not found. Initialize the database first.")
    click.echo("Profile migration complete; existing data preserved.")


def close_db(e=None):
    db=g.pop("db",None)
    if db is not None:
        db.close()
def init_db():
    """Create missing tables and indexes without deleting existing data."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        try:
            db.executescript(f.read().decode("utf8"))
        except sqlite3.Error:
            db.rollback()
            raise

@click.command("init-db")
@with_appcontext
def init_db_command():
    init_db()
    click.echo("Initialized the Roomie database")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_db_command)

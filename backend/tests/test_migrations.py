import pytest
from sqlalchemy import create_engine, inspect, text

from app.migrations import migrate

pytestmark = pytest.mark.integration


def test_additive_migration_preserves_jobs_and_runs_once():
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title VARCHAR(300))"))
            connection.execute(text("INSERT INTO jobs (id, title) VALUES (1, 'Keep this real job')"))
            migrate(connection)
            migrate(connection)
            assert connection.execute(text("SELECT title FROM jobs WHERE id=1")).scalar_one() == "Keep this real job"
            assert connection.execute(text("SELECT availability_status FROM jobs WHERE id=1")).scalar_one() is None
            assert connection.execute(text("SELECT COUNT(*) FROM career_schema_migrations")).scalar_one() == 1
            assert {"availability_status", "availability_checked_at"} <= {
                column["name"] for column in inspect(connection).get_columns("jobs")}
    finally:
        engine.dispose()

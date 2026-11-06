"""Small, versioned, additive migrations for the existing create_all project."""
from sqlalchemy import inspect, text


def migrate(connection):
    # Serialize startup schema changes on PostgreSQL, including create_all.
    connection.execute(text("CREATE TABLE IF NOT EXISTS career_schema_migrations "
                            "(version VARCHAR(100) PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
    version = "001_job_availability"
    applied = connection.execute(text("SELECT version FROM career_schema_migrations WHERE version=:version"),
                                 {"version": version}).scalar_one_or_none()
    if applied:
        return
    columns = {item["name"] for item in inspect(connection).get_columns("jobs")}
    if "availability_status" not in columns:
        connection.execute(text("ALTER TABLE jobs ADD COLUMN availability_status VARCHAR(30)"))
    if "availability_checked_at" not in columns:
        timestamp = "TIMESTAMP WITH TIME ZONE" if connection.dialect.name == "postgresql" else "TIMESTAMP"
        connection.execute(text(f"ALTER TABLE jobs ADD COLUMN availability_checked_at {timestamp}"))
    connection.execute(text("INSERT INTO career_schema_migrations (version) VALUES (:version)"), {"version": version})

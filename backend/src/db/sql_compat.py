"""SQL dialect compatibility helpers for DuckDB and Postgres."""


def upsert(
    table: str,
    columns: list[str],
    conflict_columns: list[str],
    *,
    dialect: str = "duckdb",
) -> str:
    """Generate an upsert (INSERT OR REPLACE / ON CONFLICT DO UPDATE) statement.

    Args:
        table: Table name
        columns: List of column names to insert
        conflict_columns: Columns that form the conflict/uniqueness constraint
        dialect: "duckdb" or "postgres"

    Returns:
        SQL string with ? placeholders (for DuckDB) or %s (for Postgres)
    """
    if dialect == "duckdb":
        placeholders = ", ".join(["?"] * len(columns))
        col_list = ", ".join(columns)
        return f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"

    # Postgres: INSERT ... ON CONFLICT (...) DO UPDATE SET ...
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    conflict_list = ", ".join(conflict_columns)
    update_cols = [c for c in columns if c not in conflict_columns]
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    sql += f" ON CONFLICT ({conflict_list}) DO UPDATE SET {update_set}"
    return sql


def get_dialect(db) -> str:
    """Detect the dialect from a database manager instance.

    Returns "postgres" for PostgresManager, "duckdb" otherwise.
    """
    cls_name = type(db).__name__
    if cls_name == "PostgresManager":
        return "postgres"
    return "duckdb"


def placeholder(dialect: str) -> str:
    """Return the parameter placeholder for the given dialect."""
    return "%s" if dialect == "postgres" else "?"


def user_filter(
    dialect: str,
    user_id: str,
    conditions: list[str],
    params: list,
) -> None:
    """Append a user_id filter for Postgres queries. No-op for DuckDB.

    Mutates *conditions* and *params* in place.
    """
    if dialect == "postgres":
        conditions.append(f"user_id = {placeholder(dialect)}")
        params.append(user_id)

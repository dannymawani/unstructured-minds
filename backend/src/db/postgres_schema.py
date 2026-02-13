"""Postgres schema definitions — mirrors DuckDB schema with user_id columns."""

from ..logging_config import get_logger

logger = get_logger(__name__)


def init_postgres_schema(pg, default_user_id: str) -> None:
    """Create all tables in Postgres.

    Every table gets a user_id UUID column. Composite primary keys
    include user_id where the DuckDB schema uses a single-column PK.

    Args:
        pg: PostgresManager instance
        default_user_id: UUID string for the default user
    """
    # Activities table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            date DATE NOT NULL,
            activity_type VARCHAR NOT NULL,
            duration_minutes INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, id)
        )
    """)

    # Exercise log table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS exercise_log (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            activity_id VARCHAR NOT NULL,
            date DATE NOT NULL,
            exercise_name VARCHAR NOT NULL,
            weight_kg DECIMAL(5,1),
            reps INTEGER,
            set_number INTEGER,
            duration_minutes INTEGER,
            distance_km DECIMAL(5,2),
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, id)
        )
    """)

    # Daily metrics table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS daily_metrics (
            user_id UUID NOT NULL,
            date DATE NOT NULL,
            sleep_hours DECIMAL(3,1),
            sleep_quality INTEGER,
            energy INTEGER,
            mood INTEGER,
            stress INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, date)
        )
    """)

    # Food log table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS food_log (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            date DATE NOT NULL,
            meal_type VARCHAR,
            time TIME,
            description VARCHAR,
            calories INTEGER,
            protein_g INTEGER,
            carbs_g INTEGER,
            fat_g INTEGER,
            notes VARCHAR,
            source_file VARCHAR,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, id)
        )
    """)

    # Tasks table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            status VARCHAR,
            completed_at TIMESTAMPTZ,
            category VARCHAR,
            priority INTEGER,
            source_file VARCHAR,
            deadline DATE,
            notes TEXT,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, id)
        )
    """)

    # Kanban tasks table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS kanban_tasks (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            title VARCHAR NOT NULL,
            phase VARCHAR,
            priority VARCHAR,
            status VARCHAR NOT NULL DEFAULT 'not_started',
            branch VARCHAR,
            depends_on VARCHAR,
            description VARCHAR,
            content TEXT,
            deadline DATE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            PRIMARY KEY (user_id, id)
        )
    """)

    # Kanban task updates — SERIAL id for Postgres
    pg.execute("""
        CREATE TABLE IF NOT EXISTS kanban_task_updates (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            task_id VARCHAR NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Progress reviews table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS progress_reviews (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            period_start DATE NOT NULL,
            period_end DATE NOT NULL,
            key_wins TEXT[],
            challenges TEXT[],
            work_highlights TEXT,
            training_summary TEXT,
            personal_wins TEXT[],
            health_metrics JSONB,
            goal_progress JSONB,
            focus_next TEXT[],
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, id)
        )
    """)

    # File index table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            path VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            filename VARCHAR NOT NULL,
            extension VARCHAR,
            size_bytes BIGINT,
            modified_at TIMESTAMPTZ,
            content_hash VARCHAR,
            PRIMARY KEY (user_id, path)
        )
    """)

    # Extraction log table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS extraction_log (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL,
            file_path VARCHAR NOT NULL,
            file_hash VARCHAR NOT NULL,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            success BOOLEAN,
            error_message VARCHAR
        )
    """)

    # Community exercises table (shared anonymous exercise contributions)
    pg.execute("""
        CREATE TABLE IF NOT EXISTS community_exercises (
            exercise_key VARCHAR PRIMARY KEY,
            display_name VARCHAR NOT NULL,
            aliases JSONB DEFAULT '[]',
            muscle_groups JSONB DEFAULT '[]',
            category VARCHAR DEFAULT 'other',
            recovery_hours INTEGER DEFAULT 48,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Custom extractions table
    pg.execute("""
        CREATE TABLE IF NOT EXISTS custom_extractions (
            id VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            schema_name VARCHAR NOT NULL,
            date DATE,
            data JSONB NOT NULL,
            source_file VARCHAR,
            extracted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, id)
        )
    """)

    # User settings table (JSONB key-value per user)
    pg.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id UUID NOT NULL,
            key VARCHAR NOT NULL,
            value JSONB NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, key)
        )
    """)

    # Vault files table (markdown storage for cloud mode)
    pg.execute("""
        CREATE TABLE IF NOT EXISTS vault_files (
            path VARCHAR NOT NULL,
            user_id UUID NOT NULL,
            content TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            content_hash VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, path)
        )
    """)

    # Indexes
    _create_indexes(pg)

    logger.info("postgres_schema_initialized")


def _create_indexes(pg) -> None:
    """Create performance indexes on Postgres tables."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_pg_exercise_date ON exercise_log(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_pg_metrics_date ON daily_metrics(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_pg_extraction_path ON extraction_log(user_id, file_path)",
        "CREATE INDEX IF NOT EXISTS idx_pg_food_date ON food_log(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_pg_tasks_date ON tasks(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_pg_tasks_status ON tasks(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_pg_kanban_status ON kanban_tasks(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_pg_kanban_phase ON kanban_tasks(user_id, phase)",
        "CREATE INDEX IF NOT EXISTS idx_pg_file_index_filename ON file_index(user_id, filename)",
        "CREATE INDEX IF NOT EXISTS idx_pg_reviews_period ON progress_reviews(user_id, period_start)",
        "CREATE INDEX IF NOT EXISTS idx_pg_activities_date ON activities(user_id, date)",
        "CREATE INDEX IF NOT EXISTS idx_pg_activities_type ON activities(user_id, activity_type)",
        "CREATE INDEX IF NOT EXISTS idx_pg_kanban_updates_task ON kanban_task_updates(user_id, task_id)",
        "CREATE INDEX IF NOT EXISTS idx_pg_vault_files_updated ON vault_files(user_id, updated_at)",
        # Composite indexes for common query patterns
        "CREATE INDEX IF NOT EXISTS idx_pg_exercise_name_date ON exercise_log(user_id, exercise_name, date)",
        "CREATE INDEX IF NOT EXISTS idx_pg_tasks_date_status ON tasks(user_id, date, status)",
        "CREATE INDEX IF NOT EXISTS idx_pg_activities_date_type ON activities(user_id, date, activity_type)",
        "CREATE INDEX IF NOT EXISTS idx_pg_food_date_type ON food_log(user_id, date, meal_type)",
    ]
    for sql in indexes:
        pg.execute(sql)

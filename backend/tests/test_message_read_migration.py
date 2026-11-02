from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text


def test_existing_read_times_are_preserved_as_message_ids(monkeypatch):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE room_participants (id INTEGER PRIMARY KEY, room_id INTEGER, last_read TIMESTAMP)"))
        connection.execute(text("CREATE TABLE messengers (id INTEGER PRIMARY KEY, room_messenger_id INTEGER, created_at TIMESTAMP)"))
        connection.execute(text("INSERT INTO room_participants VALUES (1, 7, '2026-11-02 06:01:00'), (2, 7, '2026-11-02 06:00:00')"))
        connection.execute(text("INSERT INTO messengers VALUES (10, 7, '2026-11-02 06:00:00'), (11, 7, '2026-11-02 06:02:00')"))

        migration_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "c3e4f5a6b7d8_add_message_read_cursor.py"
        spec = spec_from_file_location("message_read_migration", migration_path)
        assert spec and spec.loader
        migration = module_from_spec(spec)
        spec.loader.exec_module(migration)
        operations = Operations(MigrationContext.configure(connection))
        monkeypatch.setattr(migration, "op", operations)
        migration.upgrade()

        cursors = connection.execute(text("SELECT id, last_read_message_id FROM room_participants ORDER BY id")).all()
        assert cursors == [(1, 10), (2, 10)]

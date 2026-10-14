"""add optional building selection to timetable entries

Revision ID: f7a18c2d4e60
Revises: e5f6a7b8c9d0
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a18c2d4e60"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Existing campus-map coordinates; update only after verifying the campus map data.
CAMPUS_BUILDINGS = (
    ("본관", 37.276089, 127.133217),
    ("샬롬관", 37.274935, 127.130040),
    ("경천관", 37.276534, 127.133904),
    ("우원관", 37.275812, 127.131700),
    ("인사관", 37.275355, 127.130796),
    ("예술관", 37.276066, 127.130845),
    ("도서관", 37.276518, 127.132160),
    ("승리관", 37.274474, 127.132467),
    ("교육관", 37.275335, 127.133302),
    ("천은관", 37.275759, 127.134297),
    ("후생관", 37.276921, 127.133535),
    ("이공관", 37.277086, 127.134147),
    ("심전2관", 37.278582, 127.133742),
    ("심전1관", 37.278044, 127.134401),
)


def upgrade() -> None:
    op.add_column("timetable_courses", sa.Column("building_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_timetable_courses_building_id", "timetable_courses", "buildings", ["building_id"], ["id"]
    )
    op.add_column("custom_schedules", sa.Column("building_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_custom_schedules_building_id", "custom_schedules", "buildings", ["building_id"], ["id"]
    )

    connection = op.get_bind()
    insert = sa.text(
        "INSERT INTO buildings (name, latitude, longitude) "
        "SELECT :name, :latitude, :longitude "
        "WHERE NOT EXISTS (SELECT 1 FROM buildings WHERE name = :name)"
    )
    for name, latitude, longitude in CAMPUS_BUILDINGS:
        connection.execute(insert, {"name": name, "latitude": latitude, "longitude": longitude})


def downgrade() -> None:
    op.drop_constraint("fk_custom_schedules_building_id", "custom_schedules", type_="foreignkey")
    op.drop_column("custom_schedules", "building_id")
    op.drop_constraint("fk_timetable_courses_building_id", "timetable_courses", type_="foreignkey")
    op.drop_column("timetable_courses", "building_id")
    # Keep the shared buildings catalogue, including any pre-existing rows.

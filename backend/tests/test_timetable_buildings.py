from datetime import time
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.building import Building
from app.models.course import Course
from app.models.course_schedule import CourseSchedule
from app.models.custom_schedule import CustomSchedule
from app.models.room import Room
from app.models.subject import Subject
from app.models.timetable import Timetable
from app.models.timetable_course import TimetableCourse
from app.models.user import User
from app.schemas.timetable import CustomScheduleCreate, TimetableCourseCreate, TimetableCourseUpdate, TimetableDetailResponse
from app.services import timetable


class TimetableBuildingsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for model in (User, Building, Room, Subject, Course, CourseSchedule, Timetable, TimetableCourse, CustomSchedule):
            model.__table__.create(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_timetable_building_selection_and_optional_default(self):
        db = self.db
        user = User(email="building@example.com", password_hash="test", name="Student")
        building = Building(name="이공관", latitude=37.277086, longitude=127.134147)
        subject = Subject(name="첫 수업", subject_code="TEST100", credits=3, semester="2026-2")
        db.add_all([user, building, subject])
        db.flush()
        course = Course(subject_id=subject.id, section="01")
        schedule = Timetable(user_id=user.id, name="주간 시간표", semester="2026-2")
        db.add_all([course, schedule])
        db.flush()
        db.add(CourseSchedule(course_id=course.id, day_of_week="MON", start_time=time(9), end_time=time(10)))
        db.commit()

        added = timetable.add_course_to_timetable(
            db, user, schedule.id, TimetableCourseCreate(course_id=course.id)
        )
        self.assertIsNone(added.building_id)

        updated = timetable.update_timetable_course(
            db, user, schedule.id, course.id, TimetableCourseUpdate(building_id=building.id)
        )
        self.assertEqual(updated.building_id, building.id)
        detail = timetable.get_my_timetable_detail(db, user, schedule.id)
        self.assertEqual(detail["courses"][0]["building_name"], "이공관")
        self.assertEqual(detail["courses"][0]["latitude"], building.latitude)

        custom = timetable.create_custom_schedule(
            db, user, schedule.id,
            CustomScheduleCreate(
                name="개인 일정", day_of_week="TUE", start_time=time(11), end_time=time(12),
                building_id=building.id,
            ),
        )
        self.assertEqual(custom.building_name, "이공관")
        detail = timetable.get_my_timetable_detail(db, user, schedule.id)
        self.assertEqual(detail["custom_schedules"][0]["building_id"], building.id)
        response = TimetableDetailResponse.model_validate(detail)
        self.assertEqual(response.courses[0].building_name, "이공관")
        self.assertEqual(response.custom_schedules[0].building_name, "이공관")

        with self.assertRaisesRegex(ValueError, "Building not found"):
            timetable.update_timetable_course(
                db, user, schedule.id, course.id, TimetableCourseUpdate(building_id=9999)
            )


if __name__ == "__main__":
    unittest.main()

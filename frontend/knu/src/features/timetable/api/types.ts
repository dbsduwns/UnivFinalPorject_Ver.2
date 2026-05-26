import type { CourseSchedule } from "@/features/course/api/types";

export type Timetable = {
  id: number;
  user_id: number;
  name: string;
  semester: string;
  is_main: boolean;
  share_token: string | null;
  created_at: string | null;
};

export type TimetableCourse = {
  id: number;
  timetable_id: number;
  course_id: number;
  color: string;
  created_at: string | null;
};

export type TimetableCourseDetail = {
  id: number;
  subject_id: number;
  subject_code: string | null;
  name: string | null;
  credits: number | null;
  section: string;
  professor: string | null;
  color: string | null;
  schedules: CourseSchedule[];
};

export type CustomSchedule = {
  id: number;
  timetable_id: number;
  name: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  color: string;
  memo: string | null;
};

export type TimetableDetail = Timetable & {
  courses: TimetableCourseDetail[];
  custom_schedules: CustomSchedule[];
  total_credits: number;
};

export type TimetableCreateBody = {
  name: string;
  semester: string;
  is_main?: boolean;
};

export type TimetableUpdateBody = {
  name?: string;
  semester?: string;
  is_main?: boolean;
};

export type TimetableCourseCreateBody = {
  course_id: number;
  color?: string;
};

export type CustomScheduleCreateBody = {
  name: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  color?: string;
  memo?: string;
};

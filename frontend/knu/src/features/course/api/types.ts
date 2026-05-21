export type CourseSchedule = {
  id: number;
  course_id: number;
  day_of_week: string;
  start_time: string;
  end_time: string;
};

export type Subject = {
  id: number;
  name: string;
  subject_code: string;
  department: string | null;
  credits: number;
  course_type: string | null;
  semester: string;
  created_at: string | null;
};

export type Course = {
  id: number;
  subject_id: number;
  section: string;
  professor: string | null;
  max_students: number | null;
  current_students: number | null;
  created_at: string | null;
  subject: Subject | null;
  schedules: CourseSchedule[];
};

export type CourseSearchParams = {
  keyword?: string;
  department?: string;
  professor?: string;
  semester?: string;
  day_of_week?: string;
  credits?: number;
  subject_code?: string;
};

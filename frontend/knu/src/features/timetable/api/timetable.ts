import { apiClient } from "@/api/client";
import type {
  Timetable,
  TimetableCourse,
  TimetableCourseCreateBody,
  TimetableCreateBody,
  TimetableDetail,
} from "@/features/timetable/api/types";

export const getTimetables = async () => {
  const { data } = await apiClient.get<Timetable[]>("/api/timetables/");
  return data;
};

export const getTimetableDetail = async (timetableId: number) => {
  const { data } = await apiClient.get<TimetableDetail>(`/api/timetables/${timetableId}`);
  return data;
};

export const createTimetable = async (body: TimetableCreateBody) => {
  const { data } = await apiClient.post<Timetable>("/api/timetables/", body);
  return data;
};

export const addCourseToTimetable = async (
  timetableId: number,
  body: TimetableCourseCreateBody
) => {
  const { data } = await apiClient.post<TimetableCourse>(
    `/api/timetables/${timetableId}/courses`,
    body
  );
  return data;
};

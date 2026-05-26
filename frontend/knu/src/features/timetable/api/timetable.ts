import type {
  CustomSchedule,
  CustomScheduleCreateBody,
  Timetable,
  TimetableCourse,
  TimetableCourseCreateBody,
  TimetableCreateBody,
  TimetableDetail,
  TimetableUpdateBody,
} from "@/features/timetable/api/types";
import { apiClient } from "@/api/client";

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

export const updateTimetable = async (
  timetableId: number,
  body: TimetableUpdateBody
) => {
  const { data } = await apiClient.patch<Timetable>(
    `/api/timetables/${timetableId}`,
    body
  );
  return data;
};

export const deleteTimetable = async (timetableId: number) => {
  const { data } = await apiClient.delete(`/api/timetables/${timetableId}`);
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

export const removeCourseFromTimetable = async (
  timetableId: number,
  courseId: number
) => {
  const { data } = await apiClient.delete(
    `/api/timetables/${timetableId}/courses/${courseId}`
  );
  return data;
};

export const createCustomSchedule = async (
  timetableId: number,
  body: CustomScheduleCreateBody
) => {
  const { data } = await apiClient.post<CustomSchedule>(
    `/api/timetables/${timetableId}/custom-schedules`,
    body
  );
  return data;
};

export const deleteCustomSchedule = async (
  timetableId: number,
  scheduleId: number
) => {
  const { data } = await apiClient.delete(
    `/api/timetables/${timetableId}/custom-schedules/${scheduleId}`
  );
  return data;
};
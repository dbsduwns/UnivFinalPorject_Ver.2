import { apiClient } from "@/api/client";

export type AcademicCalendarEvent = {
  title: string;
  start_date: string;
  end_date: string;
};

export type AcademicCalendarMonth = {
  year: number;
  month: number;
  events: AcademicCalendarEvent[];
};

export async function getAcademicCalendarMonth(year: number, month: number) {
  const { data } = await apiClient.get<AcademicCalendarMonth>("/api/academic-calendar/", {
    params: { year, month },
  });
  return data;
}

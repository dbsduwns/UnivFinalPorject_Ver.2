import { useQueries } from "@tanstack/react-query";
import { addMonths, startOfMonth } from "date-fns";

import { getAcademicCalendarMonth } from "@/features/home/api/academic-calendar";

export function useAcademicCalendar(monthCount = 6, startDate = new Date()) {
  const firstMonth = startOfMonth(startDate);
  const months = Array.from({ length: monthCount }, (_, index) => addMonths(firstMonth, index));
  const queries = useQueries({
    queries: months.map((month) => ({
      queryKey: ["academic-calendar", month.getFullYear(), month.getMonth() + 1],
      queryFn: () => getAcademicCalendarMonth(month.getFullYear(), month.getMonth() + 1),
      staleTime: 1000 * 60 * 60,
    })),
  });

  return {
    months,
    calendar: queries.map((query, index) => query.data ?? {
      year: months[index].getFullYear(),
      month: months[index].getMonth() + 1,
      events: [],
    }),
    isLoading: queries.some((query) => query.isLoading),
    isError: queries.some((query) => query.isError),
  };
}

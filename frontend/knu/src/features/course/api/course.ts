import { apiClient } from "@/api/client";
import type { Course, CourseSearchParams } from "@/features/course/api/types";

export const getCourses = async (params: CourseSearchParams = {}) => {
  const { data } = await apiClient.get<Course[]>("/api/courses/", { params });
  return data;
};

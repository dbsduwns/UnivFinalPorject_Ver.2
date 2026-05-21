import { useMemo, useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react-native";

import { getAxiosErrorMessage } from "@/api/errors";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import { AppScrollContent } from "@/components/AppScrollContent";
import { getCourses } from "@/features/course/api/course";
import type { Course, CourseSchedule } from "@/features/course/api/types";
import {
  addCourseToTimetable,
  createTimetable,
  getTimetableDetail,
  getTimetables,
} from "@/features/timetable/api/timetable";
import type {
  CustomSchedule,
  TimetableCourseDetail,
} from "@/features/timetable/api/types";

const DAYS = [
  { key: "MON", label: "월" },
  { key: "TUE", label: "화" },
  { key: "WED", label: "수" },
  { key: "THU", label: "목" },
  { key: "FRI", label: "금" },
];

const COLORS = ["#60A5FA", "#34D399", "#F59E0B", "#A78BFA", "#F87171", "#22D3EE"];
const START_HOUR = 9;
const END_HOUR = 19;
const HOUR_HEIGHT = 56;
const DAY_WIDTH = 86;
const TIME_WIDTH = 42;

type TimetableEvent = {
  color: string;
  day: string;
  endTime: string;
  id: string;
  meta?: string | null;
  startTime: string;
  title: string;
};

const toMinutes = (time: string) => {
  const [hour, minute] = time.split(":").map(Number);
  return hour * 60 + minute;
};

const formatTime = (time: string) => time.slice(0, 5);

const formatSchedule = (schedules: CourseSchedule[]) => {
  if (schedules.length === 0) return "시간 미정";

  return schedules
    .map((schedule) => {
      const day = DAYS.find((item) => item.key === schedule.day_of_week)?.label ?? schedule.day_of_week;
      return `${day} ${formatTime(schedule.start_time)}-${formatTime(schedule.end_time)}`;
    })
    .join(", ");
};

const buildEvents = (
  courses: TimetableCourseDetail[] = [],
  customSchedules: CustomSchedule[] = []
) => {
  const courseEvents = courses.flatMap((course, courseIndex) =>
    course.schedules.map((schedule) => ({
      color: course.color ?? COLORS[courseIndex % COLORS.length],
      day: schedule.day_of_week,
      endTime: schedule.end_time,
      id: `course-${course.id}-${schedule.id}`,
      meta: course.professor,
      startTime: schedule.start_time,
      title: course.name ?? "이름 없는 과목",
    }))
  );

  const customEvents = customSchedules.map((schedule) => ({
    color: schedule.color,
    day: schedule.day_of_week,
    endTime: schedule.end_time,
    id: `custom-${schedule.id}`,
    meta: schedule.memo,
    startTime: schedule.start_time,
    title: schedule.name,
  }));

  return [...courseEvents, ...customEvents];
};

const TimetableGrid = ({ events }: { events: TimetableEvent[] }) => {
  const hours = Array.from({ length: END_HOUR - START_HOUR }, (_, index) => START_HOUR + index);
  const gridHeight = hours.length * HOUR_HEIGHT;

  const { width } = useWindowDimensions();
  const horizontalPadding = width >= 768 ? 32: 20;
  const contentWidth = Math.min(width - horizontalPadding * 2, 720);

  const timeWidth = 42;
  const dayWidth = Math.max((contentWidth - timeWidth) / DAYS.length, 64);
  const gridWidth = timeWidth + dayWidth * DAYS.length;

  return (
    <View 
      className="bg-white border border-gray-200 rounded-2xl overflow-hidden"
      style={{ width: "100%" }}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View>
          <View className="flex-row border-b border-gray-200">
            <View style={{ width: timeWidth, height: 36 }} />
            {DAYS.map((day) => (
              <View
                key={day.key}
                className="items-center justify-center"
                style={{ width: dayWidth, height: 36 }}
              >
                <Text style={{ fontSize: 13, fontWeight: "700", color: "#374151" }}>
                  {day.label}
                </Text>
              </View>
            ))}
          </View>

          <View className="flex-row">
            <View style={{ width: timeWidth, height: gridHeight }}>
              {hours.map((hour) => (
                <View key={hour} style={{ height: HOUR_HEIGHT }}>
                  <Text style={{ fontSize: 10, color: "#9CA3AF", textAlign: "center" }}>
                    {hour}
                  </Text>
                </View>
              ))}
            </View>

            <View style={{ width: DAYS.length * dayWidth, height: gridHeight }}>
              {hours.map((hour) => (
                <View
                  key={hour}
                  className="absolute left-0 right-0 border-t border-gray-100"
                  style={{ top: (hour - START_HOUR) * HOUR_HEIGHT }}
                />
              ))}

              {DAYS.map((day, index) => (
                <View
                  key={day.key}
                  className="absolute top-0 bottom-0 border-l border-gray-100"
                  style={{ left: index * dayWidth, width: dayWidth }}
                />
              ))}

              {events.map((event) => {
                const dayIndex = DAYS.findIndex((day) => day.key === event.day);
                if (dayIndex < 0) return null;

                const start = toMinutes(event.startTime);
                const end = toMinutes(event.endTime);
                const top = ((start - START_HOUR * 60) / 60) * HOUR_HEIGHT;
                const height = Math.max(((end - start) / 60) * HOUR_HEIGHT, 28);

                return (
                  <View
                    key={event.id}
                    className="absolute rounded-lg px-2 py-1"
                    style={{
                      backgroundColor: event.color,
                      height,
                      left: dayIndex * dayWidth + 3,
                      top,
                      width: dayWidth - 6,
                    }}
                  >
                    <Text numberOfLines={2} style={{ color: "white", fontSize: 11, fontWeight: "800" }}>
                      {event.title}
                    </Text>
                    <Text numberOfLines={1} style={{ color: "white", fontSize: 10 }}>
                      {formatTime(event.startTime)}-{formatTime(event.endTime)}
                    </Text>
                    {event.meta ? (
                      <Text numberOfLines={1} style={{ color: "white", fontSize: 10 }}>
                        {event.meta}
                      </Text>
                    ) : null}
                  </View>
                );
              })}
            </View>
          </View>
        </View>
      </ScrollView>
    </View>
  );
};

const CourseSearchItem = ({
  course,
  isDisabled,
  onAdd,
}: {
  course: Course;
  isDisabled: boolean;
  onAdd: () => void;
}) => (
  <View className="border border-gray-200 rounded-xl p-4 bg-white">
    <View className="flex-row justify-between">
      <View className="flex-1 pr-3">
        <Text numberOfLines={1} style={{ fontSize: 15, fontWeight: "800", color: "#111827" }}>
          {course.subject?.name ?? "이름 없는 과목"}
        </Text>
        <Text style={{ color: "#6B7280", marginTop: 4 }}>
          {course.professor ?? "교수 미정"} · {course.subject?.credits ?? 0}학점 · {course.section}분반
        </Text>
        <Text style={{ color: "#13708d", marginTop: 4 }}>
          {formatSchedule(course.schedules)}
        </Text>
      </View>
      <Pressable
        disabled={isDisabled}
        onPress={onAdd}
        className="items-center justify-center rounded-full"
        style={{
          backgroundColor: isDisabled ? "#D1D5DB" : "#1aaedb",
          height: 38,
          width: 38,
        }}
      >
        <Plus color="white" size={20}/>
      </Pressable>
    </View>
  </View>
);

export default function ScheduleScreen() {
  const queryClient = useQueryClient();
  const [newName, setNewName] = useState("나의 시간표");
  const [semester, setSemester] = useState("2026-1");
  const [keyword, setKeyword] = useState("");
  const [submittedKeyword, setSubmittedKeyword] = useState("");

  const timetablesQuery = useQuery({
    queryKey: ["timetables"],
    queryFn: getTimetables,
  });

  const currentTimetable = useMemo(() => {
    const items = timetablesQuery.data ?? [];
    return items.find((item) => item.is_main) ?? items[0] ?? null;
  }, [timetablesQuery.data]);

  const detailQuery = useQuery({
    queryKey: ["timetables", currentTimetable?.id],
    queryFn: () => getTimetableDetail(currentTimetable!.id),
    enabled: Boolean(currentTimetable?.id),
  });

  const coursesQuery = useQuery({
    queryKey: ["courses", submittedKeyword],
    queryFn: () => getCourses({ keyword: submittedKeyword || undefined }),
    enabled: submittedKeyword.trim().length > 0,
  });

  const createMutation = useMutation({
    mutationFn: createTimetable,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables"] });
    },
    onError: (err) => {
      Alert.alert("시간표 생성 실패", getAxiosErrorMessage(err));
    },
  });

  const addCourseMutation = useMutation({
    mutationFn: ({ courseId, color }: { courseId: number; color: string }) =>
      addCourseToTimetable(currentTimetable!.id, { course_id: courseId, color }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables", currentTimetable?.id] });
    },
    onError: (err) => {
      Alert.alert("과목 추가 실패", getAxiosErrorMessage(err));
    },
  });

  const events = buildEvents(detailQuery.data?.courses, detailQuery.data?.custom_schedules);

  const handleCreate = () => {
    if (!newName.trim() || !semester.trim()) {
      Alert.alert("입력 필요", "시간표 이름과 학기를 입력해주세요.");
      return;
    }

    createMutation.mutate({
      name: newName.trim(),
      semester: semester.trim(),
      is_main: !currentTimetable,
    });
  };

  const handleSearch = () => {
    setSubmittedKeyword(keyword.trim());
  };

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <View className="gap-4">
          <View className="bg-white border border-gray-200 rounded-2xl p-5">
            <Text style={{ fontSize: 22, fontWeight: "900", color: "#111827" }}>
              시간표
            </Text>
            <Text style={{ color: "#6B7280", marginTop: 6 }}>
              {currentTimetable
                ? `${currentTimetable.name} · ${currentTimetable.semester} · ${detailQuery.data?.total_credits ?? 0}학점`
                : "아직 만든 시간표가 없습니다."}
            </Text>

            <View className="flex-row gap-2 mt-4">
              <TextInput
                value={newName}
                onChangeText={setNewName}
                placeholder="시간표 이름"
                className="flex-1 border border-gray-200 rounded-xl px-3"
                style={{ height: 44 }}
              />
              <TextInput
                value={semester}
                onChangeText={setSemester}
                placeholder="학기"
                className="border border-gray-200 rounded-xl px-3"
                style={{ height: 44, width: 96 }}
              />
            </View>

            <Pressable
              onPress={handleCreate}
              disabled={createMutation.isPending}
              className="items-center justify-center rounded-xl mt-3"
              style={{ backgroundColor: "#1aaedb", height: 44 }}
            >
              <Text style={{ color: "white", fontWeight: "800" }}>
                {createMutation.isPending ? "생성 중..." : "나만의 시간표 만들기"}
              </Text>
            </Pressable>
          </View>

          {timetablesQuery.isLoading ? (
            <View className="bg-white border border-gray-200 rounded-2xl p-5">
              <Text>시간표를 불러오는 중...</Text>
            </View>
          ) : currentTimetable ? (
            <TimetableGrid events={events}/>
          ) : (
            <View className="bg-white border border-gray-200 rounded-2xl p-5">
              <Text style={{ color: "#6B7280" }}>
                시간표를 만들면 여기에 주간 시간표가 표시됩니다.
              </Text>
            </View>
          )}

          <View className="bg-white border border-gray-200 rounded-2xl p-5 gap-3">
            <Text style={{ fontSize: 18, fontWeight: "900", color: "#111827" }}>
              과목 검색
            </Text>
            <View className="flex-row gap-2">
              <TextInput
                value={keyword}
                onChangeText={setKeyword}
                placeholder="과목명, 교수명, 학수번호"
                className="flex-1 border border-gray-200 rounded-xl px-3"
                style={{ height: 44 }}
                onSubmitEditing={handleSearch}
              />
              <Pressable
                onPress={handleSearch}
                className="items-center justify-center rounded-xl"
                style={{ backgroundColor: "#13708d", height: 44, width: 48 }}
              >
                <Search color="white" size={20}/>
              </Pressable>
            </View>

            {!currentTimetable ? (
              <Text style={{ color: "#6B7280" }}>
                과목을 추가하려면 먼저 시간표를 만들어주세요.
              </Text>
            ) : null}

            {coursesQuery.isLoading ? (
              <Text>과목을 검색하는 중...</Text>
            ) : coursesQuery.data && coursesQuery.data.length > 0 ? (
              <View className="gap-3">
                {coursesQuery.data.slice(0, 20).map((course, index) => (
                  <CourseSearchItem
                    key={course.id}
                    course={course}
                    isDisabled={!currentTimetable || addCourseMutation.isPending}
                    onAdd={() =>
                      addCourseMutation.mutate({
                        courseId: course.id,
                        color: COLORS[index % COLORS.length],
                      })
                    }
                  />
                ))}
              </View>
            ) : submittedKeyword ? (
              <Text style={{ color: "#6B7280" }}>검색 결과가 없습니다.</Text>
            ) : (
              <Text style={{ color: "#6B7280" }}>
                검색어를 입력하면 개설 과목을 찾을 수 있습니다.
              </Text>
            )}
          </View>
        </View>
      </AppScrollContent>
    </AppScreenLayout>
  );
}

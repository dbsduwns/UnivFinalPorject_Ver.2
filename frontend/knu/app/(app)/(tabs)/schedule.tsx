import { useEffect, useMemo, useState } from "react";
import { useLocalSearchParams } from "expo-router";
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  useWindowDimensions,
  Modal,
} from "react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Check, ChevronDown, ChevronUp, Plus, Search, Trash2, Wand2, ChevronLeft, ChevronRight, X } from "lucide-react-native";

import { getAxiosErrorMessage } from "@/api/errors";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import { AppScrollContent } from "@/components/AppScrollContent";
import { getCourses } from "@/features/course/api/course";
import type { Course, CourseSchedule } from "@/features/course/api/types";
import {
  addCourseToTimetable,
  createCustomSchedule,
  createTimetable,
  deleteCustomSchedule,
  deleteTimetable,
  getTimetableDetail,
  getTimetables,
  removeCourseFromTimetable,
  updateTimetable,
} from "@/features/timetable/api/timetable";
import type {
  CustomSchedule,
  Timetable,
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

type TimetableEvent = {
  color: string;
  day: string;
  endTime: string;
  id: string;
  courseId?: number;
  customId?: number;
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
): TimetableEvent[] => {
  const courseEvents = courses.flatMap((course, courseIndex) =>
    course.schedules.map((schedule) => ({
      color: course.color ?? COLORS[courseIndex % COLORS.length],
      day: schedule.day_of_week,
      endTime: schedule.end_time,
      id: `course-${course.id}-${schedule.id}`,
      courseId: course.id,
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
    customId: schedule.id,
    meta: schedule.memo,
    startTime: schedule.start_time,
    title: schedule.name,
  }));

  return [...courseEvents, ...customEvents];
};

const TimetableGrid = ({ 
  events,
  onEventPress
}: {
  events: TimetableEvent[];
  onEventPress: (event: TimetableEvent) => void;
}) => {
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
        <View style={{ width: gridWidth }}>
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
                  <Pressable
                    key={event.id}
                    onPress={() => onEventPress(event)}
                    className="absolute rounded-lg px-2 py-1 active:opacity-70 shadow-sm"
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
                  </Pressable>
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

const CustomScheduleModal = ({
  visible,
  onClose,
  onSubmit,
  isPending,
}: {
  visible: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; day: string; start: string; end: string; color: string }) => void;
  isPending: boolean;
}) => {
  const [name, setName] = useState("");
  const [day, setDay] = useState("MON");
  const [startHour, setStartHour] = useState("09");
  const [startMin, setStartHourMin] = useState("00");
  const [endHour, setEndHour] = useState("10");
  const [endMin, setEndMin] = useState("00");
  const [color, setColor] = useState(COLORS[0]);

  const handleSumbit = () => {
    if (!name.trim()) return Alert.alert("입력 필요", "일정 이름을 입력해주세요.");
    onSubmit({
      name,
      day,
      start: `${startHour}:${startMin}`,
      end: `${endHour}:${endMin}`,
      color,
    });
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable className="flex-1 bg-black/50 justify-end" onPress={onClose}>
        <Pressable className="bg-white rounded-t-3xl p-6" onPress={(e) => e.stopPropagation()}>
          <Text style={{ fontSize: 20, fontWeight: "900", color: "#111827", marginBottom: 20 }}>
            직접 일정 추가
          </Text>
          
          <View className="gap-4">
            <View>
              <Text className="text-gray-500 mb-2 font-bold text-xs">일정 이름</Text>
              <TextInput
                value={name}
                onChangeText={setName}
                placeholder="예: 점심 시간, 동아리 등"
                className="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3"
              />
            </View>

            <View>
              <Text className="text-gray-500 mb-2 font-bold text-xs">요일 선택</Text>
              <View className="flex-row gap-2">
                {DAYS.map((d) => (
                  <Pressable
                    key={d.key}
                    onPress={() => setDay(d.key)}
                    className={`flex-1 py-2 rounded-xl border ${day === d.key ? 'bg-indigo-50 border-indigo-500' : 'bg-white border-gray-200'}`}
                  >
                    <Text className={`text-center font-bold ${day === d.key ? 'text-indigo-600' : 'text-gray-500'}`}>
                      {d.label}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>

            <View className="flex-row gap-4">
              <View className="flex-1">
                <Text className="text-gray-500 mb-2 font-bold text-xs">시작 시간</Text>
                <View className="flex-row items-center gap-2">
                  <TextInput
                    value={startHour}
                    onChangeText={setStartHour}
                    placeholder="09"
                    keyboardType="numeric"
                    className="flex-1 bg-gray-50 border border-gray-200 rounded-xl text-center py-2"
                  />
                  <Text>:</Text>
                  <TextInput
                    value={startMin}
                    onChangeText={setStartHourMin}
                    placeholder="00"
                    keyboardType="numeric"
                    className="flex-1 bg-gray-50 border border-gray-200 rounded-xl text-center py-2"
                  />
                </View>
              </View>
              <View className="flex-1">
                <Text className="text-gray-500 mb-2 font-bold text-xs">종료 시간</Text>
                <View className="flex-row items-center gap-2">
                  <TextInput
                    value={endHour}
                    onChangeText={setEndHour}
                    placeholder="10"
                    keyboardType="numeric"
                    className="flex-1 bg-gray-50 border border-gray-200 rounded-xl text-center py-2"
                  />
                  <Text>:</Text>
                  <TextInput
                    value={endMin}
                    onChangeText={setEndMin}
                    placeholder="00"
                    keyboardType="numeric"
                    className="flex-1 bg-gray-50 border border-gray-200 rounded-xl text-center py-2"
                  />
                </View>
              </View>
            </View>

            <View>
              <Text className="text-gray-500 mb-2 font-bold text-xs">색상 선택</Text>
              <View className="flex-row gap-3">
                {COLORS.map((c) => (
                  <Pressable
                    key={c}
                    onPress={() => setColor(c)}
                    style={{ backgroundColor: c }}
                    className={`w-8 h-8 rounded-full border-2 ${color === c ? 'border-gray-800' : 'border-transparent'}`}
                  />
                ))}
              </View>
            </View>

            <Pressable
              onPress={handleSumbit}
              disabled={isPending}
              className="bg-indigo-600 rounded-2xl py-4 mt-4"
            >
              <Text className="text-white text-center font-black text-lg">
                {isPending ? "추가 중..." : "일정 추가하기"}
              </Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
};

const EditTimetableModal = ({
  visible,
  onClose,
  onSubmit,
  onDelete,
  initialData,
}: {
  visible: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string, is_main: boolean, semester: string }) => void;
  onDelete?: () => void;
  initialData?: Timetable;
}) => {
  const [name, setName] = useState("");
  const [is_main, setIs_main] = useState(false);
  const [semester, setSemester] = useState("");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    if (initialData) {
      setName(initialData.name);
      setIs_main(initialData.is_main);
      setSemester(initialData.semester);
    } else {
      // 현재 학기 구하기
      const today = new Date();
      const year = today.getFullYear();
      const month = today.getMonth() + 1;
      let defaultNum = "1";
      if (month >= 9 && month <= 12) {
        defaultNum = "2";
      }
      setName("");
      setIs_main(false);
      setSemester(`${year}-${defaultNum}`);
    }
  }, [initialData, visible]);

  const handleSubmit = () => {
    if (!name.trim()) return Alert.alert("입력 필요", "시간표 이름을 입력해주세요.");
    onSubmit({
      name,
      is_main,
      semester,
    });
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable className="flex-1 bg-black/50 justify-end" onPress={onClose}>
        <Pressable className="bg-white rounded-t-3xl p-6 pb-10" onPress={(e) => e.stopPropagation()}>
          <View className="flex-row justify-between items-center mb-6">
            <Text style={{ fontSize: 20, fontWeight: "900", color: "#111827" }}>
              {initialData ? "시간표 수정" : "새 시간표 생성"}
            </Text>
            {initialData && onDelete && (
              <Pressable 
                onPress={onDelete}
                className="p-2 rounded-xl bg-red-50"
              >
                <Trash2 size={20} color="#EF4444" />
              </Pressable>
            )}
          </View>

          <View className="gap-4">
            <View>
              <Text className="text-gray-500 mb-2 font-bold text-xs">제목</Text>
              <TextInput
                value={name}
                onChangeText={setName}
                placeholder="예: 2026-1"
                className="bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3"
              />
            </View>

            <View style={{ zIndex: 1000 }}>
              <Text className="text-gray-500 mb-2 font-bold text-xs">학기 선택</Text>
              <Pressable
                onPress={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex-row items-center justify-between bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3"
              >
                <Text className="font-bold text-gray-900">{semester}</Text>
                {isDropdownOpen ? (
                  <ChevronUp size={20} color="#6B7280" />
                ) : (
                  <ChevronDown size={20} color="#6B7280" />
                )}
              </Pressable>

              {isDropdownOpen && (
                <View className="absolute top-[70px] left-0 right-0 bg-white border border-gray-200 rounded-2xl shadow-xl overflow-hidden">
                  {["2026-1", "2025-2", "2025-1", "2024-2"].map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => {
                        setSemester(s);
                        setIsDropdownOpen(false);
                      }}
                      className={`px-4 py-3 border-b border-gray-50 last:border-0 ${semester === s ? 'bg-indigo-50' : 'active:bg-gray-100'}`}
                    >
                      <Text className={`font-bold ${semester === s ? 'text-indigo-600' : 'text-gray-700'}`}>
                        {s}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              )}
            </View>

            <View>
              <Text className="text-gray-500 mb-2 font-bold text-xs">대표 시간표 설정</Text>
              <Pressable
                onPress={() => setIs_main(!is_main)}
                className="flex-row items-center gap-3 bg-gray-50 p-4 rounded-2xl border border-gray-200"
              >
                <View
                  style={{
                    height: 24,
                    width: 24,
                    borderRadius: 6,
                    borderWidth: 2,
                    borderColor: is_main ? '#1aaedb' : '#D1D5DB',
                    backgroundColor: is_main ? '#1aaedb' : 'white',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {is_main && <Check color="white" size={16} strokeWidth={3} />}
                </View>
                <Text className={`font-bold ${is_main ? 'text-gray-900' : 'text-gray-500'}`}>
                  이 시간표를 기본으로 사용하기
                </Text>
              </Pressable>
            </View>

            <Pressable
              onPress={handleSubmit}
              className="bg-indigo-600 rounded-2xl py-4 mt-4 shadow-sm active:opacity-90"
            >
              <Text className="text-white text-center font-black text-lg">
                {initialData ? "변경사항 저장" : "시간표 생성"}
              </Text>
            </Pressable>
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  )
}


// --- 시간표 마법사 로직 ---
const doSchedulesOverlap = (sched1: CourseSchedule, sched2: CourseSchedule) => {
  if (sched1.day_of_week !== sched2.day_of_week) return false;
  const start1 = toMinutes(sched1.start_time);
  const end1 = toMinutes(sched1.end_time);
  const start2 = toMinutes(sched2.start_time);
  const end2 = toMinutes(sched2.end_time);
  return Math.max(start1, start2) < Math.min(end1, end2); // 겹치면 true
};

const isCourseOverlapping = (course: Course, currentSelection: Course[]) => {
  for (const selected of currentSelection) {
    for (const s1 of course.schedules) {
      for (const s2 of selected.schedules) {
        if (doSchedulesOverlap(s1, s2)) return true;
      }
    }
  }
  return false;
};

const generateCombinations = (groups: Course[][], currentIdx: number, currentSelection: Course[], validCombinations: Course[][]) => {
  if (currentIdx === groups.length) {
    validCombinations.push([...currentSelection]);
    return;
  }

  const currentGroup = groups[currentIdx];
  for (const course of currentGroup) {
    if (!isCourseOverlapping(course, currentSelection)) {
      currentSelection.push(course);
      generateCombinations(groups, currentIdx + 1, currentSelection, validCombinations);
      currentSelection.pop();
    }
  }
};

const TimetableWizardModal = ({
  visible,
  onClose,
  currentTimetableId,
  onSaveCombination,
}: {
  visible: boolean;
  onClose: () => void;
  currentTimetableId: number | null | undefined;
  onSaveCombination: (courses: Course[]) => void;
}) => {
  const [keyword, setKeyword] = useState("");
  const [submittedKeyword, setSubmittedKeyword] = useState("");
  
  // 과목명 기준으로 그룹화된 선택된 강의들
  const [selectedGroups, setSelectedGroups] = useState<Record<string, Course[]>>({});
  
  // 생성된 조합들
  const [combinations, setCombinations] = useState<Course[][]>([]);
  const [currentComboIdx, setCurrentComboIdx] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const coursesQuery = useQuery({
    queryKey: ["courses", submittedKeyword],
    queryFn: () => getCourses({ keyword: submittedKeyword || undefined }),
    enabled: submittedKeyword.trim().length > 0,
  });

  // 모달 열릴 때 초기화
  useEffect(() => {
    if (visible) {
      setSelectedGroups({});
      setCombinations([]);
      setCurrentComboIdx(0);
      setKeyword("");
      setSubmittedKeyword("");
    }
  }, [visible]);

  const handleSearch = () => setSubmittedKeyword(keyword.trim());

  const handleAddCourse = (course: Course) => {
    const subjectName = course.subject?.name ?? "이름 없는 과목";
    setSelectedGroups(prev => {
      const group = prev[subjectName] || [];
      if (group.find(c => c.id === course.id)) return prev; // 이미 추가됨
      return { ...prev, [subjectName]: [...group, course] };
    });
  };

  const handleRemoveCourse = (subjectName: string, courseId: number) => {
    setSelectedGroups(prev => {
      const group = prev[subjectName].filter(c => c.id !== courseId);
      const newGroups = { ...prev };
      if (group.length === 0) {
        delete newGroups[subjectName];
      } else {
        newGroups[subjectName] = group;
      }
      return newGroups;
    });
  };

  const handleGenerate = () => {
    setIsGenerating(true);
    setTimeout(() => { // UI block 방지
      const groupsArray = Object.values(selectedGroups);
      if (groupsArray.length === 0) {
        Alert.alert("알림", "최소 1개 이상의 과목을 선택해주세요.");
        setIsGenerating(false);
        return;
      }

      const results: Course[][] = [];
      generateCombinations(groupsArray, 0, [], results);
      
      setCombinations(results);
      setCurrentComboIdx(0);
      setIsGenerating(false);
      
      if (results.length === 0) {
        Alert.alert("결과 없음", "선택한 과목들로 만들 수 있는 겹치지 않는 시간표 조합이 없습니다.");
      }
    }, 100);
  };

  // 현재 보여줄 조합을 TimetableEvent 형식으로 변환
  const comboEvents = useMemo(() => {
    if (combinations.length === 0) return [];
    const combo = combinations[currentComboIdx];
    return combo.flatMap((course, idx) => 
      course.schedules.map(schedule => ({
        color: COLORS[idx % COLORS.length],
        day: schedule.day_of_week,
        endTime: schedule.end_time,
        id: `combo-${course.id}-${schedule.id}`,
        startTime: schedule.start_time,
        title: course.subject?.name ?? "이름 없음",
        meta: course.professor
      }))
    );
  }, [combinations, currentComboIdx]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View className="flex-1 bg-gray-50 pt-12">
        <View className="px-5 pb-4 flex-row justify-between items-center border-b border-gray-200 bg-white">
          <Text style={{ fontSize: 20, fontWeight: "900", color: "#111827" }}>
            시간표 마법사 🧙
          </Text>
          <Pressable onPress={onClose} className="p-2">
            <X size={24} color="#6B7280" />
          </Pressable>
        </View>

        {combinations.length > 0 ? (
          // 결과 화면
          <View className="flex-1 p-5 gap-4">
            <View className="flex-row justify-between items-center">
              <Text style={{ fontSize: 18, fontWeight: "800", color: "#111827" }}>
                총 {combinations.length}개의 조합 중 {currentComboIdx + 1}번째
              </Text>
              <Pressable onPress={() => setCombinations([])} className="bg-gray-200 px-3 py-1.5 rounded-lg">
                <Text style={{ fontWeight: "700", color: "#4B5563" }}>다시 선택</Text>
              </Pressable>
            </View>

            <View className="flex-row justify-between items-center bg-white p-3 rounded-2xl border border-gray-200">
              <Pressable 
                disabled={currentComboIdx === 0}
                onPress={() => setCurrentComboIdx(prev => prev - 1)}
                className={`p-2 rounded-full ${currentComboIdx === 0 ? 'opacity-30' : 'bg-gray-100'}`}
              >
                <ChevronLeft size={24} color="#374151" />
              </Pressable>
              
              <Text style={{ fontWeight: "800", color: "#374151" }}>
                조합 {currentComboIdx + 1} / {combinations.length}
              </Text>
              
              <Pressable 
                disabled={currentComboIdx === combinations.length - 1}
                onPress={() => setCurrentComboIdx(prev => prev + 1)}
                className={`p-2 rounded-full ${currentComboIdx === combinations.length - 1 ? 'opacity-30' : 'bg-gray-100'}`}
              >
                <ChevronRight size={24} color="#374151" />
              </Pressable>
            </View>

            <View className="flex-1">
               <TimetableGrid events={comboEvents} onEventPress={() => {}} />
            </View>

            <Pressable
              onPress={() => onSaveCombination(combinations[currentComboIdx])}
              className="bg-indigo-600 rounded-2xl py-4 mt-2 mb-6 shadow-sm active:opacity-90"
            >
              <Text className="text-white text-center font-black text-lg">
                현재 시간표에 적용하기
              </Text>
            </Pressable>
          </View>
        ) : (
          // 과목 선택 화면
          <ScrollView className="flex-1 p-5" showsVerticalScrollIndicator={false}>
            {/* 선택된 과목 그룹 */}
            {Object.keys(selectedGroups).length > 0 && (
              <View className="mb-6 bg-white p-4 rounded-2xl border border-gray-200">
                <Text style={{ fontSize: 16, fontWeight: "800", color: "#111827", marginBottom: 12 }}>
                  선택된 과목 (총 {Object.keys(selectedGroups).length}과목)
                </Text>
                {Object.entries(selectedGroups).map(([subjectName, courses]) => (
                  <View key={subjectName} className="mb-4 last:mb-0">
                    <Text style={{ fontWeight: "700", color: "#374151", marginBottom: 6 }}>
                      {subjectName} <Text style={{ color: "#1aaedb" }}>({courses.length}개 후보)</Text>
                    </Text>
                    <View className="flex-row flex-wrap gap-2">
                      {courses.map(c => (
                        <View key={c.id} className="flex-row items-center bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5">
                          <Text style={{ fontSize: 12, color: "#4B5563" }}>{c.professor || '미정'} ({c.section}분반)</Text>
                          <Pressable onPress={() => handleRemoveCourse(subjectName, c.id)} className="ml-1.5">
                            <X size={14} color="#EF4444" />
                          </Pressable>
                        </View>
                      ))}
                    </View>
                  </View>
                ))}
                
                <Pressable
                  onPress={handleGenerate}
                  disabled={isGenerating}
                  className="bg-indigo-600 rounded-xl py-3 mt-4 active:opacity-90"
                >
                  <Text className="text-white text-center font-bold text-base">
                    {isGenerating ? "계산 중..." : "가능한 조합 생성하기"}
                  </Text>
                </Pressable>
              </View>
            )}

            <View className="flex-row gap-2 mb-4">
              <TextInput
                value={keyword}
                onChangeText={setKeyword}
                placeholder="마법사에 추가할 과목 검색"
                className="flex-1 bg-white border border-gray-200 rounded-xl px-4"
                style={{ height: 48 }}
                onSubmitEditing={handleSearch}
              />
              <Pressable
                onPress={handleSearch}
                className="items-center justify-center rounded-xl"
                style={{ backgroundColor: "#13708d", height: 48, width: 48 }}
              >
                <Search color="white" size={20}/>
              </Pressable>
            </View>

            {coursesQuery.isLoading ? (
              <ActivityIndicator size="large" color="#13708d" style={{ marginTop: 20 }} />
            ) : coursesQuery.data && coursesQuery.data.length > 0 ? (
              <View className="gap-3 pb-10">
                {coursesQuery.data.map((course) => {
                  const subjectName = course.subject?.name ?? "이름 없음";
                  const isSelected = selectedGroups[subjectName]?.some(c => c.id === course.id);
                  return (
                    <CourseSearchItem
                      key={course.id}
                      course={course}
                      isDisabled={isSelected}
                      onAdd={() => handleAddCourse(course)}
                    />
                  );
                })}
              </View>
            ) : submittedKeyword ? (
              <Text style={{ color: "#6B7280", textAlign: "center", marginTop: 20 }}>검색 결과가 없습니다.</Text>
            ) : null}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
};

export default function ScheduleScreen() {
  const queryClient = useQueryClient();
  const [selectedTimetableId, setSelectedTimetableId] = useState<number | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<TimetableEvent | null>(null);
  const [isCustomModalOpen, setIsCustomModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [timetableToEdit, setTimetableToEdit] = useState<Timetable | undefined>(undefined);
  
  const [newName, setNewName] = useState("나의 시간표");
  const [semester, setSemester] = useState("2026-1");
  const [keyword, setKeyword] = useState("");
  const [submittedKeyword, setSubmittedKeyword] = useState("");

  const timetablesQuery = useQuery({
    queryKey: ["timetables"],
    queryFn: getTimetables,
  });

  const sortedTimetables = useMemo(() => {
    if (!timetablesQuery.data) return [];
    return [...timetablesQuery.data].sort((a, b) => {
      if (a.is_main && !b.is_main) return -1;
      if (!a.is_main && b.is_main) return 1;
      return b.id - a.id;
    });
  }, [timetablesQuery.data]);

  const currentTimetableId = selectedTimetableId || 
    (timetablesQuery.data?.find((t) => t.is_main) || timetablesQuery.data?.[0])?.id;

  const detailQuery = useQuery({
    queryKey: ["timetables", currentTimetableId],
    queryFn: () => getTimetableDetail(currentTimetableId!),
    enabled: Boolean(currentTimetableId),
  });

  const coursesQuery = useQuery({
    queryKey: ["courses", submittedKeyword],
    queryFn: () => getCourses({ keyword: submittedKeyword || undefined }),
    enabled: submittedKeyword.trim().length > 0,
  });

  const createMutation = useMutation({
    mutationFn: createTimetable,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["timetables"] });
      setSelectedTimetableId(data.id);
      setIsEditModalOpen(false);
      Alert.alert("시간표 생성", "새로운 시간표가 생성되었습니다.");
    },
    onError: (err) => {
      Alert.alert("시간표 생성 실패", getAxiosErrorMessage(err));
    },
  });

  const updateTimetableMutation = useMutation({
    mutationFn: ({ id, data }: { id: number, data: any }) => updateTimetable(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables"] });
      setIsEditModalOpen(false);
    },
    onError: (err) => {
      Alert.alert("시간표 수정 실패", getAxiosErrorMessage(err));
    },
  });

  const deleteTimetableMutation = useMutation({
    mutationFn: deleteTimetable,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables"] });
      setSelectedTimetableId(null);
      setIsEditModalOpen(false);
    },
    onError: (err) => {
      Alert.alert("시간표 삭제 실패", getAxiosErrorMessage(err));
    },
  });

  const addCourseMutation = useMutation({
    mutationFn: ({ courseId, color }: { courseId: number; color: string }) =>
      addCourseToTimetable(currentTimetableId!, { course_id: courseId, color }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables", currentTimetableId] });
    },
    onError: (err) => {
      Alert.alert("과목 추가 실패", getAxiosErrorMessage(err));
    },
  });

  const removeCourseMutation = useMutation({
    mutationFn: (courseId: number) =>
      removeCourseFromTimetable(currentTimetableId!, courseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables", currentTimetableId] });
      setSelectedEvent(null);
    },
    onError: (err) => {
      Alert.alert("과목 삭제 실패", getAxiosErrorMessage(err));
    },
  });

  const addCustomMutation = useMutation({
    mutationFn: (data: { name: string; day_of_week: string; start_time: string; end_time: string; color: string }) =>
      createCustomSchedule(currentTimetableId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables", currentTimetableId] });
      setIsCustomModalOpen(false);
    },
    onError: (err) => {
      Alert.alert("일정 추가 실패", getAxiosErrorMessage(err));
    },
  });

  const removeCustomMutation = useMutation({
    mutationFn: (scheduleId: number) =>
      deleteCustomSchedule(currentTimetableId!, scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timetables", currentTimetableId] });
      setSelectedEvent(null);
    },
    onError: (err) => {
      Alert.alert("일정 삭제 실패", getAxiosErrorMessage(err));
    },
  });

  const events = useMemo(() => 
    buildEvents(detailQuery.data?.courses, detailQuery.data?.custom_schedules),
    [detailQuery.data]
  );

  const handleCreateOrUpdate = (data: { name: string, is_main: boolean, semester: string }) => {
    if (timetableToEdit) {
      updateTimetableMutation.mutate({ id: timetableToEdit.id, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleDeleteTimetable = () => {
    if (!timetableToEdit) return;
    Alert.alert(
      "시간표 삭제",
      `'${timetableToEdit.name}' 시간표를 삭제하시겠습니까?`,
      [
        { text: "취소", style: "cancel" },
        { 
          text: "삭제", 
          style: "destructive", 
          onPress: () => deleteTimetableMutation.mutate(timetableToEdit.id) 
        },
      ]
    );
  };

  const handleSearch = () => {
    setSubmittedKeyword(keyword.trim());
  };

  const handleWizard = () => {
    setIsWizardOpen(true);
  };

  const handleSaveWizardCombination = (courses: Course[]) => {
    if (!currentTimetableId) {
      Alert.alert("알림", "먼저 시간표를 선택해주세요.");
      return;
    }

    courses.forEach((course, index) => {
      addCourseMutation.mutate({
        courseId: course.id,
        color: COLORS[index % COLORS.length],
      });
    });

    setIsWizardOpen(false);

    Alert.alert(
      "완료",
      `${courses.length}개 과목이 시간표에 추가되었습니다.`
    );
  };

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <View className="gap-4">
          <View className="bg-white border border-gray-200 rounded-2xl p-5">
            <View className="flex-row justify-between items-start">
              <View className="flex-1">
                <Text style={{ fontSize: 22, fontWeight: "900", color: "#111827" }}>
                  시간표
                </Text>
                <Text style={{ color: "#6B7280", marginTop: 6 }}>
                  {detailQuery.data
                    ? `${detailQuery.data.name} · ${detailQuery.data.semester} · ${detailQuery.data.total_credits}학점`
                    : "아직 만든 시간표가 없습니다."}
                </Text>
              </View>
              <View className="flex-row gap-2">
                <Pressable
                  onPress={() => setIsCustomModalOpen(true)}
                  disabled={!currentTimetableId}
                  className="p-2.5 bg-gray-100 rounded-xl"
                >
                  <CalendarClock color={currentTimetableId ? "#4B5563" : "#D1D5DB"} size={20} />
                </Pressable>
                <Pressable
                  onPress={handleWizard}
                  className="flex-row items-center bg-indigo-50 px-3 py-2 rounded-xl"
                >
                  <Wand2 color="#6366F1" size={16} />
                  <Text className="ml-1.5 font-bold text-indigo-600 text-xs">마법사</Text>
                </Pressable>
              </View>
            </View>

            {/* 시간표 선택기 */}
            {sortedTimetables.length > 0 && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mt-4">
                <View className="flex-row gap-2">
                  {sortedTimetables.map((t) => (
                    <Pressable
                      key={t.id}
                      onPress={() => setSelectedTimetableId(t.id)}
                      onLongPress={() => {
                        setTimetableToEdit(t);
                        setIsEditModalOpen(true);
                      }}
                      className={`px-4 py-2 rounded-xl border ${currentTimetableId === t.id ? 'bg-indigo-600 border-indigo-600' : 'bg-white border-gray-200'}`}
                    >
                      <View className="flex-row items-center gap-1.5">
                        {t.is_main && (
                          <View className={`w-3 h-3 rounded-full ${currentTimetableId === t.id ? 'bg-white' : 'bg-indigo-500'}`} />
                        )}
                        <Text className={`font-bold ${currentTimetableId === t.id ? 'text-white' : 'text-gray-500'}`}>
                          {t.name}
                        </Text>
                      </View>
                    </Pressable>
                  ))}
                  <Pressable
                    onPress={() => {
                      setTimetableToEdit(undefined);
                      setIsEditModalOpen(true);
                    }}
                    className="px-4 py-2 rounded-xl border border-dashed border-gray-300 bg-gray-50"
                  >
                    <Text className="text-gray-400 font-bold">+ 추가</Text>
                  </Pressable>
                </View>
              </ScrollView>
            )}

            {!currentTimetableId && (
              <View className="mt-4">
                <Pressable
                  onPress={() => {
                    setTimetableToEdit(undefined);
                    setIsEditModalOpen(true);
                  }}
                  disabled={createMutation.isPending}
                  className="items-center justify-center rounded-xl mt-3"
                  style={{ backgroundColor: "#1aaedb", height: 44 }}
                >
                  <Text style={{ color: "white", fontWeight: "800" }}>
                    나만의 시간표 만들기
                  </Text>
                </Pressable>
              </View>
            )}
          </View>

          {timetablesQuery.isLoading ? (
            <View className="bg-white border border-gray-200 rounded-2xl p-5">
              <Text>시간표를 불러오는 중...</Text>
            </View>
          ) : currentTimetableId ? (
            <TimetableGrid 
              events={events} 
              onEventPress={(event) => setSelectedEvent(event)}
            />
          ) : (
            <View className="bg-white border border-gray-200 rounded-2xl p-5">
              <Text style={{ color: "#6B7280" }}>
                시간표를 만들면 여기에 주간 시간표가 표시됩니다.
              </Text>
            </View>
          )}

          {/* 이벤트 상세 정보 모달 */}
          <Modal
            visible={selectedEvent !== null}
            transparent={true}
            animationType="fade"
            onRequestClose={() => setSelectedEvent(null)}
          >
            <Pressable
              className="flex-1 justify-center items-center bg-black/50 px-5"
              onPress={() => setSelectedEvent(null)}
            >
              <Pressable 
                className="bg-white rounded-2xl p-6 w-full shadow-lg" 
                onPress={() => {}}
              >
                {selectedEvent && (
                  <View className="gap-2">
                    <View className="flex-row justify-between items-start">
                      <View className="flex-1 mr-2">
                        <Text style={{ fontSize: 20, fontWeight: "900", color: "#111827" }}>
                          {selectedEvent.title}
                        </Text>
                        <Text style={{ fontSize: 15, color: "#6B7280", marginTop: 4 }}>
                          {selectedEvent.meta || "정보 없음"}
                        </Text>
                      </View>
                      <View 
                        className="w-4 h-4 rounded-full" 
                        style={{ backgroundColor: selectedEvent.color }} 
                      />
                    </View>

                    <View className="bg-gray-50 p-4 rounded-xl mt-2">
                      <Text style={{ fontSize: 14, color: "#374151", fontWeight: "600" }}>
                        시간 정보
                      </Text>
                      <Text style={{ fontSize: 14, color: "#6B7280", marginTop: 4 }}>
                        {DAYS.find(d => d.key === selectedEvent.day)?.label}요일 {formatTime(selectedEvent.startTime)} - {formatTime(selectedEvent.endTime)}
                      </Text>
                    </View>

                    <View className="flex-row gap-2 mt-4">
                      <Pressable
                        onPress={() => setSelectedEvent(null)}
                        className="flex-1 items-center justify-center rounded-xl bg-gray-100"
                        style={{ height: 48 }}
                      >
                        <Text style={{ color: "#374151", fontWeight: "700" }}>닫기</Text>
                      </Pressable>
                      <Pressable
                        onPress={() => {
                          Alert.alert(
                            "일정 삭제",
                            `'${selectedEvent.title}' 일정을 시간표에서 삭제하시겠습니까?`,
                            [
                              { text: "취소", style: "cancel" },
                              { 
                                text: "삭제", 
                                style: "destructive", 
                                onPress: () => {
                                  if (selectedEvent.courseId) {
                                    removeCourseMutation.mutate(selectedEvent.courseId);
                                  } else if (selectedEvent.customId) {
                                    removeCustomMutation.mutate(selectedEvent.customId);
                                  }
                                } 
                              },
                            ]
                          );
                        }}
                        className="flex-1 flex-row items-center justify-center rounded-xl bg-red-50"
                        style={{ height: 48 }}
                      >
                        <Trash2 color="#EF4444" size={18} />
                        <Text style={{ color: "#EF4444", fontWeight: "700", marginLeft: 6 }}>
                          삭제
                        </Text>
                      </Pressable>
                    </View>
                  </View>
                )}
              </Pressable>
            </Pressable>
          </Modal>

          {/* 커스텀 일정 추가 모달 */}
          <CustomScheduleModal
            visible={isCustomModalOpen}
            onClose={() => setIsCustomModalOpen(false)}
            isPending={addCustomMutation.isPending}
            onSubmit={(data) => {
              addCustomMutation.mutate({
                name: data.name,
                day_of_week: data.day,
                start_time: data.start,
                end_time: data.end,
                color: data.color,
              });
            }}
          />

          {/* 시간표 삭제 및 수정 모달 */}
          <EditTimetableModal
            visible={isEditModalOpen}
            onClose={() => setIsEditModalOpen(false)}
            initialData={timetableToEdit}
            onSubmit={handleCreateOrUpdate}
            onDelete={handleDeleteTimetable}
          />

          {/* 시간표 마법사 모달 */}
          <TimetableWizardModal
            visible={isWizardOpen}
            onClose={() => setIsWizardOpen(false)}
            currentTimetableId={currentTimetableId}
            onSaveCombination={handleSaveWizardCombination}
          />

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

            {!currentTimetableId ? (
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
                    isDisabled={!currentTimetableId || addCourseMutation.isPending}
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
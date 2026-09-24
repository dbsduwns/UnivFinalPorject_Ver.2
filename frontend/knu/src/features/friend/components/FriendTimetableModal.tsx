import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  Pressable,
  ScrollView,
  ActivityIndicator,
  useWindowDimensions,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { X, Calendar, ChevronDown, BookOpen, Clock, User, Award } from "lucide-react-native";

import { getFriendTimetable } from "../api/friend";
import type { TimetableDetail, TimetableCourseDetail, CustomSchedule } from "@/features/timetable/api/types";

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
  rawCourse?: TimetableCourseDetail;
  rawCustom?: CustomSchedule;
};

const toMinutes = (time: string) => {
  const [hour, minute] = time.split(":").map(Number);
  return hour * 60 + minute;
};

const formatTime = (time: string) => time.slice(0, 5);

type Props = {
  visible: boolean;
  friendId: number | null;
  friendName?: string;
  onClose: () => void;
};

export const FriendTimetableModal = ({ visible, friendId, friendName, onClose }: Props) => {
  const [selectedTimetableId, setSelectedTimetableId] = useState<number | undefined>(undefined);
  const [selectedEvent, setSelectedEvent] = useState<TimetableEvent | null>(null);

  const { width } = useWindowDimensions();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["friendTimetable", friendId, selectedTimetableId],
    queryFn: () => (friendId ? getFriendTimetable(friendId, selectedTimetableId) : null),
    enabled: visible && !!friendId,
  });

  const timetable = data?.timetable;
  const friend = data?.friend;
  const availableTimetables = data?.available_timetables ?? [];

  // Build events
  const events: TimetableEvent[] = React.useMemo(() => {
    if (!timetable) return [];
    const courseEvents = (timetable.courses ?? []).flatMap((course, idx) =>
      course.schedules.map((schedule) => ({
        color: course.color ?? COLORS[idx % COLORS.length],
        day: schedule.day_of_week,
        endTime: schedule.end_time,
        id: `course-${course.id}-${schedule.id}`,
        courseId: course.id,
        meta: course.professor,
        startTime: schedule.start_time,
        title: course.name ?? "과목",
        rawCourse: course,
      }))
    );

    const customEvents = (timetable.custom_schedules ?? []).map((custom) => ({
      color: custom.color ?? "#9CA3AF",
      day: custom.day_of_week,
      endTime: custom.end_time,
      id: `custom-${custom.id}`,
      customId: custom.id,
      meta: custom.memo,
      startTime: custom.start_time,
      title: custom.name,
      rawCustom: custom,
    }));

    return [...courseEvents, ...customEvents];
  }, [timetable]);

  const hours = Array.from({ length: END_HOUR - START_HOUR }, (_, i) => START_HOUR + i);
  const gridHeight = hours.length * HOUR_HEIGHT;
  const contentWidth = Math.min(width - 40, 680);
  const timeWidth = 38;
  const dayWidth = Math.max((contentWidth - timeWidth) / DAYS.length, 60);
  const gridWidth = timeWidth + dayWidth * DAYS.length;

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View className="flex-1 bg-black/50 justify-end sm:justify-center items-center">
        <View className="bg-[#F8FAFC] w-full sm:w-[92%] max-w-2xl h-[90%] rounded-t-3xl sm:rounded-3xl overflow-hidden flex-col shadow-2xl">
          {/* Header */}
          <View className="bg-white px-5 py-4 border-b border-gray-200 flex-row items-center justify-between">
            <View className="flex-row items-center space-x-3">
              <View className="w-10 h-10 rounded-full bg-sky-100 items-center justify-center">
                <Calendar size={20} color="#0284C7" />
              </View>
              <View>
                <Text className="text-lg font-bold text-gray-900">
                  {friend?.name ?? friendName ?? "친구"} 님의 시간표
                </Text>
                <Text className="text-xs text-gray-500">
                  {friend?.department ? `${friend.department} · ` : ""}
                  {friend?.student_id ? `${friend.student_id}` : ""}
                </Text>
              </View>
            </View>

            <Pressable
              onPress={onClose}
              className="p-2 rounded-full bg-gray-100 active:bg-gray-200"
            >
              <X size={20} color="#475569" />
            </Pressable>
          </View>

          {/* Body */}
          {isLoading ? (
            <View className="flex-1 items-center justify-center">
              <ActivityIndicator size="large" color="#0284C7" />
              <Text className="mt-3 text-sm text-gray-500">시간표를 불러오는 중입니다...</Text>
            </View>
          ) : isError ? (
            <View className="flex-1 items-center justify-center px-6">
              <Text className="text-base font-semibold text-rose-500 text-center">
                시간표를 불러올 수 없습니다.
              </Text>
              <Text className="text-xs text-gray-500 text-center mt-1">
                {(error as any)?.response?.data?.detail || "친구 관계가 아니거나 오류가 발생했습니다."}
              </Text>
            </View>
          ) : !timetable ? (
            <View className="flex-1 items-center justify-center px-6">
              <Calendar size={48} color="#CBD5E1" />
              <Text className="text-base font-semibold text-gray-600 mt-4">
                등록된 시간표가 없습니다.
              </Text>
              <Text className="text-xs text-gray-400 mt-1">
                친구가 아직 이번 학기 시간표를 작성하지 않았습니다.
              </Text>
            </View>
          ) : (
            <ScrollView className="flex-1 px-4 py-3" showsVerticalScrollIndicator={false}>
              {/* Timetable Selector & Credits Bar */}
              <View className="bg-white p-3 rounded-2xl border border-gray-200 mb-3 flex-row items-center justify-between">
                <View className="flex-row items-center flex-1 mr-2">
                  <Text className="text-sm font-bold text-gray-800 mr-2" numberOfLines={1}>
                    {timetable.name} ({timetable.semester})
                  </Text>
                  {timetable.is_main && (
                    <View className="bg-sky-100 px-2 py-0.5 rounded-md">
                      <Text className="text-[10px] font-bold text-sky-700">대표</Text>
                    </View>
                  )}
                </View>

                {availableTimetables.length > 1 && (
                  <View className="flex-row items-center space-x-1">
                    {availableTimetables.map((t) => (
                      <Pressable
                        key={t.id}
                        onPress={() => setSelectedTimetableId(t.id)}
                        className={`px-2.5 py-1 rounded-lg border ${
                          (selectedTimetableId ?? timetable.id) === t.id
                            ? "bg-sky-600 border-sky-600"
                            : "bg-gray-50 border-gray-200"
                        }`}
                      >
                        <Text
                          className={`text-xs font-semibold ${
                            (selectedTimetableId ?? timetable.id) === t.id
                              ? "text-white"
                              : "text-gray-600"
                          }`}
                        >
                          {t.name}
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                )}

                <View className="flex-row items-center ml-2 bg-amber-50 px-2 py-1 rounded-lg border border-amber-200">
                  <Award size={13} color="#D97706" />
                  <Text className="text-xs font-bold text-amber-800 ml-1">
                    {timetable.total_credits}학점
                  </Text>
                </View>
              </View>

              {/* Grid */}
              <View className="bg-white border border-gray-200 rounded-2xl overflow-hidden mb-6">
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View style={{ width: gridWidth }}>
                    {/* Weekday Header */}
                    <View className="flex-row border-b border-gray-200 bg-gray-50">
                      <View style={{ width: timeWidth, height: 36 }} />
                      {DAYS.map((day) => (
                        <View
                          key={day.key}
                          className="items-center justify-center border-l border-gray-200"
                          style={{ width: dayWidth, height: 36 }}
                        >
                          <Text style={{ fontSize: 13, fontWeight: "700", color: "#334155" }}>
                            {day.label}
                          </Text>
                        </View>
                      ))}
                    </View>

                    {/* Hours & Grid Lines */}
                    <View className="flex-row">
                      {/* Time Column */}
                      <View style={{ width: timeWidth, height: gridHeight }} className="bg-gray-50/50">
                        {hours.map((hour) => (
                          <View key={hour} style={{ height: HOUR_HEIGHT }} className="items-center pt-1">
                            <Text style={{ fontSize: 10, color: "#94A3B8", fontWeight: "600" }}>
                              {hour}
                            </Text>
                          </View>
                        ))}
                      </View>

                      {/* Day Columns */}
                      <View style={{ width: DAYS.length * dayWidth, height: gridHeight }}>
                        {hours.map((hour) => (
                          <View
                            key={hour}
                            className="absolute left-0 right-0 border-t border-gray-100"
                            style={{ top: (hour - START_HOUR) * HOUR_HEIGHT }}
                          />
                        ))}

                        {DAYS.map((day, idx) => (
                          <View
                            key={day.key}
                            className="absolute top-0 bottom-0 border-l border-gray-100"
                            style={{ left: idx * dayWidth, width: dayWidth }}
                          />
                        ))}

                        {/* Events Blocks */}
                        {events.map((event) => {
                          const dayIndex = DAYS.findIndex((d) => d.key === event.day);
                          if (dayIndex < 0) return null;

                          const start = toMinutes(event.startTime);
                          const end = toMinutes(event.endTime);
                          const top = ((start - START_HOUR * 60) / 60) * HOUR_HEIGHT;
                          const height = Math.max(((end - start) / 60) * HOUR_HEIGHT, 28);

                          return (
                            <Pressable
                              key={event.id}
                              onPress={() => setSelectedEvent(event)}
                              className="absolute rounded-lg px-1.5 py-1 active:opacity-75 shadow-sm overflow-hidden"
                              style={{
                                backgroundColor: event.color,
                                height,
                                left: dayIndex * dayWidth + 2,
                                top,
                                width: dayWidth - 4,
                              }}
                            >
                              <Text
                                numberOfLines={2}
                                style={{ color: "white", fontSize: 10, fontWeight: "800" }}
                              >
                                {event.title}
                              </Text>
                              <Text numberOfLines={1} style={{ color: "white", fontSize: 9 }}>
                                {formatTime(event.startTime)}-{formatTime(event.endTime)}
                              </Text>
                              {event.meta ? (
                                <Text numberOfLines={1} style={{ color: "white", fontSize: 9 }}>
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
            </ScrollView>
          )}

          {/* Event Detail Modal (Click on class) */}
          <Modal
            visible={!!selectedEvent}
            animationType="fade"
            transparent
            onRequestClose={() => setSelectedEvent(null)}
          >
            <View className="flex-1 bg-black/40 items-center justify-center px-6">
              <View className="bg-white w-full max-w-sm rounded-2xl p-5 shadow-2xl">
                <View className="flex-row items-center justify-between pb-3 border-b border-gray-100">
                  <View className="flex-row items-center space-x-2 flex-1">
                    <View
                      className="w-3.5 h-3.5 rounded-full"
                      style={{ backgroundColor: selectedEvent?.color }}
                    />
                    <Text className="text-base font-bold text-gray-900 flex-1" numberOfLines={1}>
                      {selectedEvent?.title}
                    </Text>
                  </View>
                  <Pressable
                    onPress={() => setSelectedEvent(null)}
                    className="p-1 rounded-full bg-gray-100"
                  >
                    <X size={16} color="#64748B" />
                  </Pressable>
                </View>

                <View className="mt-4 space-y-2.5">
                  {selectedEvent?.rawCourse?.subject_code && (
                    <View className="flex-row items-center justify-between">
                      <Text className="text-xs text-gray-500">학수번호</Text>
                      <Text className="text-xs font-semibold text-gray-800">
                        {selectedEvent.rawCourse.subject_code} (분반: {selectedEvent.rawCourse.section})
                      </Text>
                    </View>
                  )}

                  {selectedEvent?.rawCourse?.professor && (
                    <View className="flex-row items-center justify-between">
                      <Text className="text-xs text-gray-500">담당교수</Text>
                      <Text className="text-xs font-semibold text-gray-800">
                        {selectedEvent.rawCourse.professor}
                      </Text>
                    </View>
                  )}

                  {selectedEvent?.rawCourse?.credits && (
                    <View className="flex-row items-center justify-between">
                      <Text className="text-xs text-gray-500">학점</Text>
                      <Text className="text-xs font-semibold text-gray-800">
                        {selectedEvent.rawCourse.credits}학점
                      </Text>
                    </View>
                  )}

                  <View className="flex-row items-center justify-between">
                    <Text className="text-xs text-gray-500">강의 시간</Text>
                    <Text className="text-xs font-semibold text-sky-700">
                      {DAYS.find((d) => d.key === selectedEvent?.day)?.label ?? selectedEvent?.day}요일{" "}
                      {selectedEvent && formatTime(selectedEvent.startTime)} ~{" "}
                      {selectedEvent && formatTime(selectedEvent.endTime)}
                    </Text>
                  </View>

                  {selectedEvent?.meta && (
                    <View className="pt-2 border-t border-gray-100">
                      <Text className="text-[11px] text-gray-500">메모 / 정보</Text>
                      <Text className="text-xs text-gray-700 mt-0.5">{selectedEvent.meta}</Text>
                    </View>
                  )}
                </View>

                <Pressable
                  onPress={() => setSelectedEvent(null)}
                  className="mt-5 w-full py-2.5 bg-gray-100 rounded-xl items-center active:bg-gray-200"
                >
                  <Text className="text-xs font-bold text-gray-700">닫기</Text>
                </Pressable>
              </View>
            </View>
          </Modal>
        </View>
      </View>
    </Modal>
  );
};

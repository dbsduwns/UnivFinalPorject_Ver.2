import { useMemo, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, View } from "react-native";
import { CalendarDays, ChevronLeft, ChevronRight, X } from "lucide-react-native";
import { addMonths, eachDayOfInterval, endOfMonth, endOfWeek, format, isSameMonth, isToday, parseISO, startOfMonth, startOfWeek } from "date-fns";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { AppScrollContent } from "@/components/ui/AppScrollContent";
import type { AcademicCalendarEvent } from "@/features/home/api/academic-calendar";
import { useAcademicCalendar } from "@/features/home/hooks/use-academic-calendar";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];
const DAY_WIDTH = 100 / 7;

const getAcademicYearStart = () => {
  const now = new Date();
  const year = now.getMonth() < 2 ? now.getFullYear() - 1 : now.getFullYear();
  return startOfMonth(new Date(year, 2, 1));
};

const isEventOnDate = (event: AcademicCalendarEvent, day: Date) => {
  const date = format(day, "yyyy-MM-dd");
  return event.start_date <= date && event.end_date >= date;
};

const formatEventRange = (event: AcademicCalendarEvent) => (
  event.start_date === event.end_date
    ? format(parseISO(event.start_date), "M월 d일")
    : `${format(parseISO(event.start_date), "M월 d일")} - ${format(parseISO(event.end_date), "M월 d일")}`
);

export default function AcademicCalendarScreen() {
  const academicYearStart = useMemo(getAcademicYearStart, []);
  const [selectedMonth, setSelectedMonth] = useState(startOfMonth(new Date()));
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);
  const { calendar, isLoading, isError } = useAcademicCalendar(12, academicYearStart);
  const selectedData = calendar.find(
    (item) => item.year === selectedMonth.getFullYear() && item.month === selectedMonth.getMonth() + 1,
  );

  const monthOptions = useMemo(
    () => Array.from({ length: 12 }, (_, index) => addMonths(academicYearStart, index)),
    [academicYearStart],
  );

  const weeks = useMemo(() => {
    const days = eachDayOfInterval({
      start: startOfWeek(startOfMonth(selectedMonth), { weekStartsOn: 0 }),
      end: endOfWeek(endOfMonth(selectedMonth), { weekStartsOn: 0 }),
    });
    return Array.from({ length: Math.ceil(days.length / 7) }, (_, index) => days.slice(index * 7, index * 7 + 7));
  }, [selectedMonth]);

  const selectedDayEvents = selectedDay && selectedData?.events.filter((event) => isEventOnDate(event, selectedDay));

  return (
    <AppScreenLayout>
      <AppScrollContent>
        <View className="flex-row items-center">
          <CalendarDays color="#13708D" size={24} />
          <Text className="ml-2 text-xl font-extrabold text-gray-900">전체 학사일정</Text>
        </View>

        <View className="rounded-2xl border border-gray-200 bg-white p-4">
          <View className="mb-3 flex-row items-center justify-between">
            <Pressable
              className="h-9 w-9 items-center justify-center rounded-full bg-gray-50"
              onPress={() => setSelectedMonth((month) => addMonths(month, -1))}
              disabled={selectedMonth.getTime() <= monthOptions[0].getTime()}
            >
              <ChevronLeft color="#13708D" size={20} />
            </Pressable>
            <Text className="text-base font-extrabold text-gray-900">{format(selectedMonth, "yyyy년 M월")}</Text>
            <Pressable
              className="h-9 w-9 items-center justify-center rounded-full bg-gray-50"
              onPress={() => setSelectedMonth((month) => addMonths(month, 1))}
              disabled={selectedMonth.getTime() >= addMonths(monthOptions[0], 11).getTime()}
            >
              <ChevronRight color="#13708D" size={20} />
            </Pressable>
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-4" contentContainerStyle={{ gap: 8 }}>
            {monthOptions.map((month) => {
              const selected = format(month, "yyyy-MM") === format(selectedMonth, "yyyy-MM");
              return (
                <Pressable
                  key={month.toISOString()}
                  className={`rounded-lg px-3 py-2 ${selected ? "bg-[#13708D]" : "bg-gray-50"}`}
                  onPress={() => setSelectedMonth(month)}
                >
                  <Text className={`text-[11px] font-bold ${selected ? "text-white" : "text-gray-500"}`}>
                    {format(month, "yyyy.MM")}
                  </Text>
                </Pressable>
              );
            })}
          </ScrollView>

          <View className="flex-row border-b border-gray-100 pb-2">
            {WEEKDAYS.map((day, index) => (
              <Text key={day} className={`flex-1 text-center text-xs font-bold ${index === 0 ? "text-rose-400" : index === 6 ? "text-blue-400" : "text-gray-400"}`}>
                {day}
              </Text>
            ))}
          </View>

          <View>
            {weeks.map((week) => {
              const weekStart = week[0];
              const weekEnd = week[6];
              const weekEvents = selectedData?.events.filter((event) => event.start_date <= format(weekEnd, "yyyy-MM-dd") && event.end_date >= format(weekStart, "yyyy-MM-dd")) ?? [];
              return (
                <View key={weekStart.toISOString()} className="relative h-[76px] flex-row">
                  {week.map((day) => {
                    const inMonth = isSameMonth(day, selectedMonth);
                    return (
                      <Pressable
                        key={day.toISOString()}
                        className="h-[76px] items-center pt-2"
                        style={{ width: `${DAY_WIDTH}%` }}
                        onPress={() => setSelectedDay(day)}
                      >
                        <View className={`h-7 w-7 items-center justify-center rounded-full ${isToday(day) ? "bg-[#13708D]" : ""}`}>
                          <Text className={`text-xs font-semibold ${!inMonth ? "text-gray-200" : isToday(day) ? "text-white" : day.getDay() === 0 ? "text-rose-400" : day.getDay() === 6 ? "text-blue-400" : "text-gray-700"}`}>
                            {format(day, "d")}
                          </Text>
                        </View>
                      </Pressable>
                    );
                  })}
                  {weekEvents.slice(0, 3).map((event, eventIndex) => {
                    const start = Math.max(0, week.findIndex((day) => format(day, "yyyy-MM-dd") >= event.start_date));
                    const end = Math.min(6, week.findLastIndex((day) => format(day, "yyyy-MM-dd") <= event.end_date));
                    const eventStartIndex = week.findIndex((day) => format(day, "yyyy-MM-dd") === event.start_date);
                    return end >= start ? (
                      <View key={`${event.title}-${event.start_date}`}>
                        <View
                          className="absolute h-1.5 rounded-full bg-[#A7C7D8]"
                          style={{ left: `${start * DAY_WIDTH + 2}%`, top: 43 + eventIndex * 7, width: `${(end - start + 1) * DAY_WIDTH - 4}%` }}
                        />
                        {eventStartIndex >= 0 && (
                          <View
                            className="absolute h-2.5 w-2.5 rounded-full bg-[#F97316]"
                            style={{ left: `${eventStartIndex * DAY_WIDTH + 1.2}%`, top: 41 + eventIndex * 7 }}
                          />
                        )}
                      </View>
                    ) : null;
                  })}
                </View>
              );
            })}
          </View>
        </View>

        <View>
          <Text className="mb-3 text-[15px] font-bold text-gray-900">{format(selectedMonth, "M월 일정")}</Text>
          {isLoading ? (
            <View className="items-center rounded-2xl border border-gray-200 bg-white p-8">
              <ActivityIndicator size="small" color="#1aaedb" />
              <Text className="mt-2 text-xs text-gray-400">학사일정을 불러오는 중...</Text>
            </View>
          ) : isError ? (
            <View className="rounded-2xl border border-gray-200 bg-white p-8">
              <Text className="text-center text-xs text-gray-400">학사일정을 불러오지 못했어요.</Text>
            </View>
          ) : selectedData?.events.length ? (
            <View className="rounded-2xl border border-gray-200 bg-white p-4">
              {selectedData.events.map((event, index) => (
                <View key={`${event.start_date}-${event.title}`} className={`flex-row ${index ? "mt-3 border-t border-gray-100 pt-3" : ""}`}>
                  <Text className="mr-3 w-[92px] text-xs font-bold text-[#13708D]">{formatEventRange(event)}</Text>
                  <Text className="flex-1 text-sm font-semibold leading-5 text-gray-700">{event.title}</Text>
                </View>
              ))}
            </View>
          ) : (
            <View className="rounded-2xl border border-gray-200 bg-white p-8">
              <Text className="text-center text-xs text-gray-400">등록된 일정이 없습니다.</Text>
            </View>
          )}
        </View>

        <Modal visible={Boolean(selectedDay)} transparent animationType="fade" onRequestClose={() => setSelectedDay(null)}>
          <View className="flex-1 items-center justify-center bg-black/40 px-6">
            <View className="w-full rounded-3xl bg-white p-5">
              <View className="mb-4 flex-row items-center justify-between">
                <View>
                  <Text className="text-xs font-semibold text-[#13708D]">선택한 날짜</Text>
                  <Text className="mt-1 text-lg font-extrabold text-gray-900">{selectedDay ? format(selectedDay, "yyyy년 M월 d일") : ""}</Text>
                </View>
                <Pressable className="h-9 w-9 items-center justify-center rounded-full bg-gray-50" onPress={() => setSelectedDay(null)}>
                  <X color="#6B7280" size={18} />
                </Pressable>
              </View>
              {selectedDayEvents?.length ? selectedDayEvents.map((event) => (
                <View key={`${event.start_date}-${event.title}`} className="mb-3 rounded-xl bg-[#E8F7FB] p-3">
                  <Text className="text-sm font-bold text-[#13708D]">{event.title}</Text>
                  <Text className="mt-1 text-xs text-gray-500">{formatEventRange(event)}</Text>
                </View>
              )) : <Text className="py-5 text-center text-sm text-gray-400">이 날짜에는 예정된 일정이 없습니다.</Text>}
            </View>
          </View>
        </Modal>
      </AppScrollContent>
    </AppScreenLayout>
  );
}

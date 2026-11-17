import { ActivityIndicator, Pressable, Text, View } from "react-native";
import { CalendarDays, ChevronRight } from "lucide-react-native";
import { router } from "expo-router";

import { useAcademicCalendar } from "@/features/home/hooks/use-academic-calendar";
import type { AcademicCalendarEvent } from "@/features/home/api/academic-calendar";

const formatDate = (value: string, month: number) => {
  const day = Number(value.slice(-2));
  const valueMonth = Number(value.slice(5, 7));
  return valueMonth === month ? `${day}일` : `${value.slice(5, 7)}/${day}`;
};

const formatRange = (event: AcademicCalendarEvent, month: number) => {
  const start = formatDate(event.start_date, month);
  const end = formatDate(event.end_date, month);
  return start === end ? start : `${start} - ${end}`;
};

export function AcademicCalendar() {
  const { calendar, isLoading, isError } = useAcademicCalendar(1);

  return (
    <View className="w-full">
      <View className="mb-3 flex-row items-center justify-between">
        <View className="flex-row items-center">
          <CalendarDays color="#13708D" size={22} />
          <Text className="ml-2 text-[15px] font-bold text-gray-900">학사일정</Text>
        </View>
        <Pressable
          className="flex-row items-center"
          onPress={() => router.push("/(app)/(tabs)/academic-calendar" as never)}
        >
          <Text className="mr-1 text-xs font-semibold text-[#13708D]">전체보기</Text>
          <ChevronRight color="#13708D" size={16} />
        </Pressable>
      </View>

      {isLoading ? (
        <View className="h-36 items-center justify-center rounded-2xl border border-gray-200 bg-white">
          <ActivityIndicator size="small" color="#1aaedb" />
          <Text className="mt-2 text-xs text-gray-400">학사일정을 불러오는 중...</Text>
        </View>
      ) : isError ? (
        <View className="h-36 items-center justify-center rounded-2xl border border-gray-200 bg-white px-6">
          <Text className="text-center text-xs text-gray-400">학사일정을 불러오지 못했어요.</Text>
        </View>
      ) : (
        <View>
          {calendar.map((month) => (
            <View key={`${month.year}-${month.month}`} className="w-full rounded-2xl border border-gray-200 bg-white p-5">
              <View className="mb-4 flex-row items-end justify-between">
                <Text className="text-lg font-extrabold text-gray-900">{month.month}월</Text>
                <Text className="text-xs font-medium text-gray-400">{month.year} 학사일정</Text>
              </View>
              {month.events.length === 0 ? (
                <View className="h-20 items-center justify-center rounded-xl bg-gray-50">
                  <Text className="text-xs text-gray-400">등록된 일정이 없습니다.</Text>
                </View>
              ) : (
                <View>
                  {month.events.slice(0, 4).map((event, index) => (
                    <View key={`${event.start_date}-${event.title}`} className={`flex-row ${index > 0 ? "mt-3 border-t border-gray-100 pt-3" : ""}`}>
                      <View className="mr-3 min-w-[52px] rounded-lg bg-[#E8F7FB] px-2 py-1.5">
                        <Text className="text-center text-[11px] font-bold text-[#13708D]">{formatRange(event, month.month)}</Text>
                      </View>
                      <Text className="flex-1 text-xs font-semibold leading-5 text-gray-700" numberOfLines={2}>{event.title}</Text>
                    </View>
                  ))}
                  {month.events.length > 4 && <Text className="mt-3 text-right text-[11px] font-medium text-gray-400">+ {month.events.length - 4}개 일정 더보기</Text>}
                </View>
              )}
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

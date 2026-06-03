import { Pressable, Text, View, ActivityIndicator, TouchableOpacity } from "react-native";
import { Calendar, ChevronRight } from "lucide-react-native";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";

import { getTimetables, getTimetableDetail } from "@/features/timetable/api/timetable";
import { useMemo } from "react";

interface ScheduleItem {
    id: number | string;
    name: string | null;
    room: string;
    professor: string | null;
    startTime: string;
    endTime: string;
    credits: number | null;
    type: 'course' | 'custom';
    memo?: string | null;
}

const getTodayDayOfWeek = () => {
    const days = [ "SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT" ];
    return days[new Date().getDay()];
};

export const TodaySchedule = () => {
    const today = getTodayDayOfWeek();

    // 1. 전체 시간표 목록에서 메인 시간표 찾기
    const { data: timetables, isLoading: isListLoading } = useQuery({
        queryKey: ["timetables"],
        queryFn: getTimetables,
    });

    const mainTimetableId = timetables?.find(t => t.is_main)?.id;

    // 2. 메인 시간표의 상세 데이터 가져오기
    const { data: detail, isLoading: isDetailLoading } = useQuery({
        queryKey: ["timetables", mainTimetableId],
        queryFn: () => getTimetableDetail(mainTimetableId!),
        enabled: !!mainTimetableId,
    });

    // 3. 오늘 요일에 해당하는 수업 및 개인 일정 필터링 및 정렬
    const todayLectures = useMemo(() => {
        if (!detail) return [];

        const items: ScheduleItem[] = [];

        // 일반 강의
        detail.courses.forEach(course => {
            course.schedules.forEach(schedule => {
                if (schedule.day_of_week === today) {
                    items.push({
                        id: `course-${course.id}`,
                        name: course.name,
                        professor: course.professor,
                        room: "강의실 정보",
                        startTime: schedule.start_time.substring(0, 5),
                        endTime: schedule.end_time.substring(0, 5),
                        credits: course.credits,
                        type: 'course',
                    });
                }
            });
        });

        // 개인 일정
        detail.custom_schedules.forEach(custom => {
            if (custom.day_of_week === today) {
                items.push({
                    id: `custom-${custom.id}`,
                    name: custom.name,
                    professor: null,
                    room: "개인 일정",
                    startTime: custom.start_time.substring(0, 5),
                    endTime: custom.end_time.substring(0, 5),
                    credits: null,
                    type: 'custom',
                    memo: custom.memo,
                });
            }
        });

        // 시간 순서대로 정렬
        return items.sort((a, b) => a.startTime.localeCompare(b.startTime));
    }, [detail, today]);

    // 현재 진행 중인 강의 확인 로직
    const nowStr = useMemo(() => {
        const now = new Date();
        return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    }, []);

    const isCurrentLecture = (start: string, end: string) => {
        return nowStr >= start && nowStr <= end;
    };

    if (isListLoading || isDetailLoading) {
        return (
            <View className="w-full bg-white border border-gray-200 rounded-[15px] p-10 items-center justify-center">
                <ActivityIndicator size="small" color="#1aaedb" />
                <Text className="mt-2 text-gray-400 text-xs">시간표를 불러오는 중...</Text>
            </View>
        );
    }

    return (
        <View
            className="TodaySchedule justify-center flex-col"
            style={{
                backgroundColor: 'white',
                borderWidth: 1,
                borderRadius: 15,
                borderColor: '#E5E7EB',
                width: "100%",
            }}
        >
            {/* 헤더 */}
            <View className="ScheduleTitle flex-row justify-between mx-6 mt-6">
                <View className="flex-row items-center">
                    <View className="IconCalendar mr-2">
                        <Calendar color={'#1aaedb'} size={ 24 } />
                    </View>
                    <View className="Title">
                        <Text style={{ fontSize: 15, fontWeight: 'bold' }}>
                            오늘의 시간표
                        </Text>
                    </View>
                </View>
                
                <Pressable
                    className="flex-row items-center"
                    onPress={() => router.push("/(app)/(tabs)/schedule")}
                >
                    <Text style={{ color: '#1aaedb', fontSize: 12, marginRight: 2 }}>
                        전체보기
                    </Text>
                    <ChevronRight color={'#1aaedb'} size={16} />
                </Pressable>
            </View>

            {/* 강의 리스트 */}
            <View className="LectureCardWrapper mt-4 mb-6">
                {todayLectures.length > 0 ? (
                    todayLectures.map((lecture, index) => {
                        const active = isCurrentLecture(lecture.startTime, lecture.endTime);
                        
                        return (
                            <TouchableOpacity
                                key={`${lecture.id}-${index}`}
                                onPress={() => router.push({
                                    pathname: "/(app)/(tabs)/schedule",
                                    params: { eventId: lecture.id }
                                })}
                            >
                                <View>
                                    <View 
                                        className={`flex-row items-center px-6 py-4 ${active ? 'bg-blue-50/50' : ''}`}
                                    >
                                        {/* 시작 시간 */}
                                        <View className="w-16">
                                            <Text style={{ 
                                                color: active ? '#2563eb' : '#1aaedb', 
                                                fontWeight: 'bold', 
                                                fontSize: 16 
                                            }}>
                                                {lecture.startTime}
                                            </Text>
                                            <Text style={{ color: '#9CA3AF', fontSize: 10, marginTop: 2 }}>
                                                ~ {lecture.endTime}
                                            </Text>
                                        </View>
                                        
                                        {/* 구분선 */}
                                        <View className={`w-[1px] h-10 mx-4 ${active ? 'bg-blue-200' : 'bg-gray-100'}`} />

                                        {/* 강의 정보 */}
                                        <View className="flex-1">
                                            <View className="flex-row items-center">
                                                <Text style={{ 
                                                    fontWeight: 'bold', 
                                                    fontSize: 14, 
                                                    color: active ? '#1E40AF' : '#1F2937' 
                                                }} numberOfLines={1}>
                                                    {lecture.name}
                                                </Text>
                                                {active && (
                                                    <View className="ml-2 bg-blue-600 px-1.5 py-0.5 rounded">
                                                        <Text className="text-[10px] text-white font-bold">진행 중</Text>
                                                    </View>
                                                )}
                                            </View>
                                            <Text style={{ color: active ? '#60A5FA' : '#6B7280', fontSize: 12, marginTop: 1 }}>
                                                {lecture.type === 'course' 
                                                    ? `${lecture.professor} · ${lecture.credits}학점` 
                                                    : (lecture.memo || "메모 없음")}
                                            </Text>
                                        </View>
                                    </View>
                                    {index < todayLectures.length - 1 && (
                                        <View className="h-[1px] bg-gray-50 mx-8" />
                                    )}
                                </View>
                            </TouchableOpacity>
                        );
                    })
                ) : (
                    <View className="py-10 items-center">
                        <Text className="text-gray-400 text-sm">오늘 예정된 수업이 없습니다.</Text>
                    </View>
                )}
            </View>
        </View>
    );
};

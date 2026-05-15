import { Pressable, Text, View, ScrollView, TextInput, useWindowDimensions } from "react-native";
import { Calendar, ChevronRight } from "lucide-react-native";

export const TodaySchedule = () => {
    
    return (       
        // Today's Schedule Card
        <View 
            className="TodaySchedule justify-center flex-col mx-5 mt-5"
            style={{ 
                backgroundColor: 'white',
                borderWidth: 1,
                borderRadius: 15,
                borderColor: '#E5E7EB',
            }}>
            {/* [ Header ] => Icon / Title / See All Button */}
            <View className="ScheduleTitle flex-row justify-between mx-2 mt-6">
                {/* Icon */}
                <View 
                    className="IconCalendar ml-4 mr-2 mt-1">
                    <Calendar color={ '#1aaedb' } size={ 28 }/>
                </View>
                {/* Title */}
                <View
                    className="Title mt-1">
                    <Text 
                        style={{ fontSize: 15, fontWeight: 'bold' }}>
                            오늘의 시간표
                    </Text>
                </View>
                {/* See All Icon */}
                <Pressable 
                    className="flex-row">
                    <Text 
                        className="mt-1"
                        style={{ 
                            color: '#1aaedb',
                            fontSize: 12
                        }}>전체보기</Text>
                    <View className="mt-1">
                        <ChevronRight color={ '#1aaedb' }/>
                    </View>
                </Pressable>
            </View>
            {/* Lecture Card */}
            <View className="LectureCardWrapper my-6">
                <View
                    className="flex-row">
                    {/* Time */}
                    <View
                        className="m-7">
                        <Text style={{ color: '#1aaedb', fontWeight: 'bold' }}>
                            09:00
                        </Text>
                    </View>
                    {/* Lecture Info */}
                    <View
                        className="m-3">
                        {/* Lecture Name & Class Room */}
                        <View>
                            <Text style={{ fontWeight: 'bold' }}>
                                자료구조 / 이공관 201호
                            </Text>
                        </View>
                        {/* Professor & Credit */}
                        <View><Text>김교수 · 3학점</Text></View>
                    </View>
                </View>
                <View className="h-[1px] bg-gray-100 w-full mx-8"></View>
                <View
                    className="flex-row">
                    {/* Time */}
                    <View
                        className="m-7">
                        <Text style={{ color: '#1aaedb', fontWeight: 'bold' }}>
                            11:50
                        </Text>
                    </View>
                    {/* Lecture Info */}
                    <View
                        className="m-3">
                        {/* Lecture Name & Class Room */}
                        <View>
                            <Text style={{ fontWeight: 'bold' }}>
                                인공지능 개론 / 후생관 B102호
                            </Text>
                        </View>
                        {/* Professor & Credit */}
                        <View><Text>이교수 · 3학점</Text></View>
                    </View>
                </View>
            </View>
        </View>

    )
}
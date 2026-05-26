import { Text, View, Image, TouchableOpacity, ScrollView, ActivityIndicator, Platform } from "react-native";
import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, addDays, startOfWeek, isSameDay } from "date-fns";
import { ko } from "date-fns/locale";

import { AppScreenLayout } from "@/components/AppScreenLayout";
import { getDailyMenu } from "@/features/menu/menu";
import { API_BASE_URL } from "@/constants/config";
import { Download, ChevronLeft, ChevronRight, Utensils } from "lucide-react-native";

import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

export default function MealScreen() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [isDownloading, setIsDownloading] = useState(false);

  // 현재 날짜가 포함된 주의 날짜들 계산 (월~금)
  const weekDays = useMemo(() => {
    const start = startOfWeek(selectedDate, { weekStartsOn: 1 }); // 월요일 시작
    return Array.from({ length: 5 }).map((_, i) => addDays(start, i));
  }, [selectedDate]);

  const dateKey = format(selectedDate, "yyyy-MM-dd");

  const { data: menus = [], isLoading } = useQuery({
    queryKey: ["daily-menu", dateKey],
    queryFn: () => getDailyMenu(dateKey),
  });

  const menu = menus[0];

  const getFullUrl = (url: string) => {
    if (!url) return "";
    if (url.startsWith("http")) return url;
    return `${API_BASE_URL}${url}`;
  };

  const handleDownload = async () => {
    if (!menu?.image_url) return;
    
    const fullUrl = getFullUrl(menu.image_url);
    
    try {
      setIsDownloading(true);
      const fileName = `meal_menu_${dateKey}.jpg`;
      
      if (!FileSystem.documentDirectory) {
        throw new Error("문서 디렉토리를 찾을 수 없습니다.");
      }
      
      const fileUri = `${FileSystem.documentDirectory}${fileName}`;
      const downloadRes = await FileSystem.downloadAsync(fullUrl, fileUri);

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(downloadRes.uri);
      } else {
        alert("이 기기에서는 파일을 공유할 수 없습니다.");
      }
    } catch (error) {
      console.error("이미지 다운로드 실패:", error);
      alert("이미지를 불러오는 중 오류가 발생했습니다.");
    } finally {
      setIsDownloading(false);
    }
  };

  const changeWeek = (amount: number) => {
    setSelectedDate(prev => addDays(prev, amount * 7));
  };

  return (
    <AppScreenLayout>
      <View className="flex-1 bg-white">
        {/* 날짜 선택 헤더 */}
        <View className="px-4 py-4 border-b border-gray-100">
          <View className="flex-row justify-between items-center mb-4">
            <TouchableOpacity onPress={() => changeWeek(-1)} className="p-2">
              <ChevronLeft size={20} color="#6B7280" />
            </TouchableOpacity>
            <Text className="text-lg font-bold text-gray-900">
              {format(weekDays[0], "yyyy년 M월", { locale: ko })}
            </Text>
            <TouchableOpacity onPress={() => changeWeek(1)} className="p-2">
              <ChevronRight size={20} color="#6B7280" />
            </TouchableOpacity>
          </View>

          <View className="flex-row justify-between">
            {weekDays.map((day, idx) => {
              const isSelected = isSameDay(day, selectedDate);
              const dayName = format(day, "eee", { locale: ko });
              const dayNum = format(day, "d");

              return (
                <TouchableOpacity
                  key={idx}
                  onPress={() => setSelectedDate(day)}
                  className={`items-center justify-center w-14 py-3 rounded-2xl ${
                    isSelected ? "bg-blue-600" : "bg-gray-50"
                  }`}
                >
                  <Text className={`text-xs mb-1 ${isSelected ? "text-blue-100" : "text-gray-500"}`}>
                    {dayName}
                  </Text>
                  <Text className={`text-base font-bold ${isSelected ? "text-white" : "text-gray-900"}`}>
                    {dayNum}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        {/* 식단 이미지 영역 */}
        <ScrollView contentContainerStyle={{ flexGrow: 1 }} className="flex-1">
          {isLoading ? (
            <View className="flex-1 justify-center items-center py-20">
              <ActivityIndicator size="large" color="#2563eb" />
              <Text className="mt-4 text-gray-500">식단표를 불러오는 중...</Text>
            </View>
          ) : menu?.image_url ? (
            <View className="p-4">
              <View className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                <Image
                  source={{ uri: getFullUrl(menu.image_url) }}
                  style={{ width: '100%', aspectRatio: 1.5, resizeMode: 'contain' }}
                />
              </View>
              
              <TouchableOpacity 
                onPress={handleDownload}
                disabled={isDownloading}
                className={`mt-6 flex-row items-center justify-center py-4 rounded-2xl shadow-sm ${
                  isDownloading ? "bg-gray-400" : "bg-blue-600"
                }`}
              >
                {isDownloading ? (
                  <ActivityIndicator color="white" className="mr-2" />
                ) : (
                  <Download size={20} color="white" className="mr-2" />
                )}
                <Text className="text-white font-bold text-lg">
                  {isDownloading ? "준비 중..." : "식단표 저장/공유"}
                </Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View className="flex-1 justify-center items-center py-20 px-10">
              <View className="bg-gray-100 p-8 rounded-full mb-6">
                <Utensils size={64} color="#9CA3AF" />
              </View>
              <Text className="text-xl font-bold text-gray-900 mb-2">등록된 식단이 없습니다</Text>
              <Text className="text-gray-500 text-center">
                해당 날짜의 식단표가 아직 업데이트되지 않았거나{"\n"}식당 운영 정보가 없습니다.
              </Text>
            </View>
          )}
        </ScrollView>
      </View>
    </AppScreenLayout>
  );
}

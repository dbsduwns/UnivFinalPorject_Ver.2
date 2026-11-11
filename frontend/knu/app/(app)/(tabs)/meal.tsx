import { Text, View, Image, TouchableOpacity, ActivityIndicator } from "react-native";
import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { format, addDays, startOfWeek, isSameDay } from "date-fns";
import { ko } from "date-fns/locale";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { getDailyMenu } from "@/features/menu/menu";
import { API_BASE_URL } from "@/constants/config";
import { Download, ChevronLeft, ChevronRight, Utensils } from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import Animated, { useSharedValue, useAnimatedStyle, clamp, withTiming } from "react-native-reanimated";
import { Gesture, GestureDetector, GestureHandlerRootView } from "react-native-gesture-handler";

import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

function ZoomableImage({ uri }: { uri: string }) {
  const MIN_SCALE = 1;
  const MAX_SCALE = 5;
  const DOUBLE_TAP_SCALE = 2.5;

  const scale = useSharedValue(MIN_SCALE);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedTranslateX = useSharedValue(0);
  const savedTranslateY = useSharedValue(0);
  const containerWidth = useSharedValue(0);
  const containerHeight = useSharedValue(0);

  const pinchStartScale = useSharedValue(MIN_SCALE);
  const pinchStartTranslateX = useSharedValue(0);
  const pinchStartTranslateY = useSharedValue(0);
  const pinchStartFocalX = useSharedValue(0);
  const pinchStartFocalY = useSharedValue(0);
  const panStartTranslateX = useSharedValue(0);
  const panStartTranslateY = useSharedValue(0);

  // 같은 이미지를 다시 그리는 리렌더링에서는 줌을 유지하고,
  // 날짜가 바뀌어 이미지 URI가 바뀐 경우에만 초기화한다.
  useEffect(() => {
    scale.value = MIN_SCALE;
    translateX.value = 0;
    translateY.value = 0;
    savedTranslateX.value = 0;
    savedTranslateY.value = 0;
  }, [uri, scale, translateX, translateY, savedTranslateX, savedTranslateY]);

  const pinchGesture = useMemo(() => Gesture.Pinch()
    .onStart((event) => {
      pinchStartScale.value = scale.value;
      pinchStartTranslateX.value = translateX.value;
      pinchStartTranslateY.value = translateY.value;
      pinchStartFocalX.value = event.focalX - containerWidth.value / 2;
      pinchStartFocalY.value = event.focalY - containerHeight.value / 2;
    })
    .onUpdate((event) => {
      const nextScale = clamp(
        pinchStartScale.value * event.scale,
        MIN_SCALE,
        MAX_SCALE,
      );
      const scaleRatio = nextScale / pinchStartScale.value;
      const currentFocalX = event.focalX - containerWidth.value / 2;
      const currentFocalY = event.focalY - containerHeight.value / 2;

      scale.value = nextScale;
      translateX.value = currentFocalX - scaleRatio * (
        pinchStartFocalX.value - pinchStartTranslateX.value
      );
      translateY.value = currentFocalY - scaleRatio * (
        pinchStartFocalY.value - pinchStartTranslateY.value
      );
    })
    .onEnd(() => {
      if (scale.value <= MIN_SCALE) {
        scale.value = MIN_SCALE;
        translateX.value = 0;
        translateY.value = 0;
        savedTranslateX.value = 0;
        savedTranslateY.value = 0;
        return;
      }

      savedTranslateX.value = translateX.value;
      savedTranslateY.value = translateY.value;
    }), [containerHeight, containerWidth, pinchStartFocalX, pinchStartFocalY,
      pinchStartScale, pinchStartTranslateX, pinchStartTranslateY, scale,
      savedTranslateX, savedTranslateY, translateX, translateY]);

  const panGesture = useMemo(() => Gesture.Pan()
    .maxPointers(1)
    // 짧은 터치는 부모/다른 버튼으로 전달하고, 실제 드래그부터 팬을 시작한다.
    .minDistance(8)
    .onStart(() => {
      panStartTranslateX.value = translateX.value;
      panStartTranslateY.value = translateY.value;
    })
    .onUpdate((event) => {
      if (scale.value <= MIN_SCALE) return;

      const maxX = (containerWidth.value * (scale.value - 1)) / 2;
      const maxY = (containerHeight.value * (scale.value - 1)) / 2;
      translateX.value = clamp(
        panStartTranslateX.value + event.translationX,
        -maxX,
        maxX,
      );
      translateY.value = clamp(
        panStartTranslateY.value + event.translationY,
        -maxY,
        maxY,
      );
    })
    .onEnd(() => {
      savedTranslateX.value = translateX.value;
      savedTranslateY.value = translateY.value;
    }), [containerHeight, containerWidth, panStartTranslateX,
      panStartTranslateY, scale, savedTranslateX, savedTranslateY,
      translateX, translateY]);

  const doubleTap = useMemo(() => Gesture.Tap()
    .numberOfTaps(2)
    .onEnd(() => {
      const nextScale = scale.value > MIN_SCALE ? MIN_SCALE : DOUBLE_TAP_SCALE;
      scale.value = withTiming(nextScale);
      translateX.value = withTiming(0);
      translateY.value = withTiming(0);
      savedTranslateX.value = 0;
      savedTranslateY.value = 0;
    }), [savedTranslateX, savedTranslateY, scale, translateX, translateY]);

  // Exclusive로 더블 탭을 우선하면 두 손가락 핀치가 더블 탭 판정을
  // 기다리다가 실패하는 기기/버전이 있다. 세 제스처를 동시에 연결하면
  // 두 손가락은 핀치, 확대 후 한 손가락은 팬, 두 번의 짧은 터치는
  // 더블 탭으로 각각 처리된다.
  const composed = useMemo(
    () => Gesture.Simultaneous(pinchGesture, panGesture, doubleTap),
    [doubleTap, panGesture, pinchGesture],
  );

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value }
    ],
  }));

  return (
    <GestureHandlerRootView 
      style={{ flex: 1 }}
      onLayout={(e) => {
        const { width, height } = e.nativeEvent.layout;

        containerWidth.value = width;
        containerHeight.value = height;
      }}>
      <GestureDetector gesture={composed}>
        <Animated.View collapsable={false} style={[{ flex: 1 }, animatedStyle]}>
          <Image
            source={{ uri }}
            style={{ width: "100%", height: "100%" }}
            resizeMode="contain"
          />
        </Animated.View>
      </GestureDetector>
    </GestureHandlerRootView>
  );
}

const parseMenuDate = (value?: string) => {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(year, month - 1, day);
  return parsed.getFullYear() === year
    && parsed.getMonth() === month - 1
    && parsed.getDate() === day
    ? parsed
    : null;
};

export default function MealScreen() {
  const { date } = useLocalSearchParams<{ date?: string | string[] }>();
  const dateParam = Array.isArray(date) ? date[0] : date;

  const [selectedDate, setSelectedDate] = useState(
    () => parseMenuDate(dateParam) ?? new Date()
  );
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    const parsed = parseMenuDate(dateParam);
    if (parsed) setSelectedDate(parsed);
  }, [dateParam]);

  const weekDays = useMemo(() => {
    const start = startOfWeek(selectedDate, { weekStartsOn: 1 });
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
    const absoluteUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;
    try {
      const parsed = new URL(absoluteUrl);
      if (
        parsed.protocol === "https:" &&
        parsed.hostname === "web.kangnam.ac.kr" &&
        parsed.pathname.startsWith("/comm/cmnFile/")
      ) {
        return `${API_BASE_URL}/api/notices/image-proxy?url=${encodeURIComponent(absoluteUrl)}`;
      }
    } catch {
      return absoluteUrl;
    }
    return absoluteUrl;
  };

  const handleDownload = async () => {
    if (!menu?.image_url) return;
    const fullUrl = getFullUrl(menu.image_url);
    try {
      setIsDownloading(true);
      const fileName = `meal_menu_${dateKey}.jpg`;
      if (!FileSystem.documentDirectory) throw new Error("문서 디렉토리를 찾을 수 없습니다.");
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
        {isLoading ? (
          <View className="flex-1 justify-center items-center">
            <ActivityIndicator size="large" color="#2563eb" />
            <Text className="mt-4 text-gray-500">식단표를 불러오는 중...</Text>
          </View>
        ) : menu?.image_url ? (
          <>
            <View className="flex-1 p-4">
              <View className="flex-1 bg-white rounded-3xl border border-gray-100 overflow-hidden">
                <ZoomableImage uri={getFullUrl(menu.image_url)} />
              </View>
            </View>

            <SafeAreaView edges={["bottom"]}>
              <View className="px-4 pb-4">
                <TouchableOpacity
                  onPress={handleDownload}
                  disabled={isDownloading}
                  className={`flex-row items-center justify-center py-4 rounded-2xl ${
                    isDownloading ? "bg-gray-400" : "bg-blue-600"
                  }`}
                >
                  {isDownloading ? (
                    <ActivityIndicator color="white" />
                  ) : (
                    <Download size={20} color="white" />
                  )}
                  <Text className="text-white font-bold text-lg ml-2">
                    {isDownloading ? "준비 중..." : "식단표 저장/공유"}
                  </Text>
                </TouchableOpacity>
              </View>
            </SafeAreaView>
          </>
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
      </View>
    </AppScreenLayout>
  );
}

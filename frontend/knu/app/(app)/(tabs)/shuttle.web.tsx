import { Text, View, TouchableOpacity, ActivityIndicator, Linking } from "react-native";
import { useState } from "react";

import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { getShuttles } from "@/features/shuttle/api/shuttle";
import { getCurrentSemester } from "@/features/shuttle/utils/semester";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { Download, FileText } from "lucide-react-native";
import { API_BASE_URL } from "@/constants/config";

export default function ShuttleScreen() {
  const { semester: semesterParam } = useLocalSearchParams<{
    semester?: string | string[];
  }>();
  const semester = Array.isArray(semesterParam)
    ? semesterParam[0]
    : semesterParam || getCurrentSemester();
  const [isOpening, setIsOpening] = useState(false);

  const { data: shuttles = [], isLoading } = useQuery({
    queryKey: ["shuttles", semester],
    queryFn: () => getShuttles({ semester }),
  });

  const shuttle = shuttles[0];
  const getFullUrl = (url: string) => {
    if (!url) return "";
    if (url.startsWith("http")) {
      const parsed = new URL(url);
      if (parsed.hostname === "web.kangnam.ac.kr" && parsed.pathname.startsWith("/comm/cmnFile/")) {
        parsed.protocol = "https:";
        return `${API_BASE_URL}/api/notices/pdf-proxy?url=${encodeURIComponent(parsed.toString())}`;
      }
      return url;
    }
    return `${API_BASE_URL}${url}`;
  };

  const openPDF = async () => {
    if (!shuttle?.file_url) return;
    try {
      setIsOpening(true);
      await Linking.openURL(getFullUrl(shuttle.file_url));
    } finally {
      setIsOpening(false);
    }
  };

  return (
    <AppScreenLayout>
      {isLoading ? (
        <View className="flex-1 justify-center items-center">
          <ActivityIndicator size="large" color="#2563eb" />
          <Text className="mt-4 text-gray-500">셔틀 시간표를 불러오는 중...</Text>
        </View>
      ) : !shuttle ? (
        <View className="flex-1 justify-center items-center p-4">
          <Text className="text-gray-400">등록된 셔틀 시간표가 없습니다.</Text>
        </View>
      ) : (
        <View className="flex-1 justify-center items-center bg-white p-6">
          <FileText size={56} color="#2563eb" />
          <Text className="mt-5 text-lg font-bold text-gray-900 text-center">
            셔틀 시간표 PDF
          </Text>
          <Text className="mt-2 text-gray-500 text-center">
            웹에서는 PDF를 새 탭에서 엽니다.
          </Text>
          <TouchableOpacity
            className="mt-6 flex-row items-center gap-2 px-6 py-3 bg-blue-600 rounded-xl"
            onPress={openPDF}
            disabled={isOpening}
          >
            {isOpening ? <ActivityIndicator color="white" /> : <Download size={20} color="white" />}
            <Text className="text-white font-bold">PDF 열기</Text>
          </TouchableOpacity>
        </View>
      )}
    </AppScreenLayout>
  );
}

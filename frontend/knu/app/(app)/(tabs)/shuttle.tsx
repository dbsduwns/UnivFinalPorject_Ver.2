import { Alert, Text, View, Pressable, ActivityIndicator, Linking } from "react-native";
import { useState } from "react";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { getShuttles } from "@/features/shuttle/api/shuttle";
import { getCurrentSemester } from "@/features/shuttle/utils/semester";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { Download, ExternalLink } from "lucide-react-native";
import { API_BASE_URL } from "@/constants/config";
import PdfPreview from "@/components/shuttle/PdfPreview";

export default function ShuttleScreen() {
  const { semester: semesterParam } = useLocalSearchParams<{
    semester?: string | string[];
  }>();
  const semester = Array.isArray(semesterParam)
    ? semesterParam[0]
    : semesterParam || getCurrentSemester();
  const [isOpening, setIsOpening] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

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
    } catch (error) {
      console.error("셔틀 PDF 열기 실패:", error);
      alert("PDF를 열 수 없습니다.");
    } finally {
      setIsOpening(false);
    }
  };

  const downloadPDF = async () => {
    if (!shuttle?.file_url || !FileSystem.documentDirectory) return;
    try {
      setIsDownloading(true);
      const filename = `shuttle-${semester.replace(/[^a-zA-Z0-9가-힣_-]/g, "_")}.pdf`;
      const destination = `${FileSystem.documentDirectory}${filename}`;
      const { uri, status } = await FileSystem.downloadAsync(getFullUrl(shuttle.file_url), destination);
      if (status < 200 || status >= 300) throw new Error(`PDF 다운로드 실패 (HTTP ${status})`);

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, {
          mimeType: "application/pdf",
          dialogTitle: "셔틀 시간표 저장 또는 공유",
        });
      } else {
        Alert.alert("다운로드 완료", "PDF가 앱 문서함에 저장되었습니다.");
      }
    } catch (error) {
      console.error("셔틀 PDF 다운로드 실패:", error);
      Alert.alert("다운로드 실패", "PDF를 다운로드하지 못했습니다.");
    } finally {
      setIsDownloading(false);
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
        <View className="flex-1 bg-white">
          <View className="flex-1 min-h-0 w-full">
            <PdfPreview sourceUrl={getFullUrl(shuttle.file_url)} />
          </View>
          <View className="border-t border-gray-200 bg-white px-4 pt-3 pb-3">
            <View className="flex-row gap-3">
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="PDF 다운로드"
                className="flex-1 flex-row items-center justify-center rounded-xl border border-blue-200 bg-blue-50 py-3"
                onPress={downloadPDF}
                disabled={isDownloading || isOpening}
              >
                {isDownloading ? <ActivityIndicator color="#2563eb" /> : <Download size={19} color="#2563eb" />}
                <Text className="ml-2 font-bold text-blue-700">다운로드</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="PDF 외부에서 열기"
                className="flex-1 flex-row items-center justify-center rounded-xl bg-blue-600 py-3"
                onPress={openPDF}
                disabled={isOpening || isDownloading}
              >
                {isOpening ? <ActivityIndicator color="white" /> : <ExternalLink size={19} color="white" />}
                <Text className="ml-2 font-bold text-white">외부에서 열기</Text>
              </Pressable>
            </View>
          </View>
        </View>
      )}
    </AppScreenLayout>
  );
}

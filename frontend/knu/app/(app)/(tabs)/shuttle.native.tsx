import { Text, View, TouchableOpacity, ActivityIndicator } from "react-native";
import { useEffect, useState } from "react";

import { useQuery } from "@tanstack/react-query";
import { useLocalSearchParams } from "expo-router";
import { getShuttles } from "@/features/shuttle/api/shuttle";
import { getCurrentSemester } from "@/features/shuttle/utils/semester";
import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { Download, AlertCircle } from "lucide-react-native";
import { API_BASE_URL } from "@/constants/config";

import Pdf from "react-native-pdf";
import * as FileSystem from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";

export default function ShuttleScreen() {
  const { semester: semesterParam } = useLocalSearchParams<{
    semester?: string | string[];
  }>();
  const semester = Array.isArray(semesterParam)
    ? semesterParam[0]
    : semesterParam || getCurrentSemester();
  const [isDownloading, setIsDownloading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [previewUri, setPreviewUri] = useState<string | null>(null);
  const [previewAttempt, setPreviewAttempt] = useState(0);

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

  const fullPdfUrl = shuttle?.file_url ? getFullUrl(shuttle.file_url) : null;

  useEffect(() => {
    let isCurrent = true;
    setPreviewUri(null);
    setHasError(false);

    if (!fullPdfUrl || !FileSystem.cacheDirectory) {
      if (fullPdfUrl) setHasError(true);
      return () => {
        isCurrent = false;
      };
    }

    const localUri = `${FileSystem.cacheDirectory}shuttle_preview_${Date.now()}.pdf`;
    FileSystem.downloadAsync(fullPdfUrl, localUri)
      .then(({ uri, status }) => {
        if (status < 200 || status >= 300) {
          throw new Error(`PDF 다운로드 실패 (HTTP ${status})`);
        }
        if (isCurrent) setPreviewUri(uri);
      })
      .catch((error) => {
        console.error("셔틀 PDF 미리보기 다운로드 실패:", error);
        if (isCurrent) setHasError(true);
      });

    return () => {
      isCurrent = false;
    };
  }, [fullPdfUrl, previewAttempt]);

  const openPDF = async (pdfUrl: string) => {
    if (!pdfUrl) return;

    try {
      setIsDownloading(true);
      const fullUrl = getFullUrl(pdfUrl);
      if (!FileSystem.documentDirectory) {
        throw new Error("문서 디렉토리를 찾을 수 없습니다.");
      }
      const fileUri = `${FileSystem.documentDirectory}shuttle_schedule_${Date.now()}.pdf`;
      const downloadRes = await FileSystem.downloadAsync(fullUrl, fileUri);

      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(downloadRes.uri);
      } else {
        alert("이 기기에서는 파일을 공유할 수 없습니다.");
      }
    } catch (error) {
      console.error("PDF 열기 실패:", error);
      alert("PDF를 불러오는 중 오류가 발생했습니다.");
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
          <View className="flex-1">
            {hasError ? (
              <View className="flex-1 justify-center items-center p-6">
                <AlertCircle size={48} color="#ef4444" />
                <Text className="mt-4 text-lg font-bold text-gray-900 text-center">
                  미리보기를 불러올 수 없습니다
                </Text>
                <Text className="mt-2 text-gray-500 text-center">
                  네트워크 상태를 확인하거나 아래 버튼을 눌러{"\n"}
                  직접 파일을 열어주세요.
                </Text>
                <TouchableOpacity
                  onPress={() => setPreviewAttempt((attempt) => attempt + 1)}
                  className="mt-6 px-6 py-3 bg-gray-100 rounded-xl"
                >
                  <Text className="text-gray-700 font-medium">다시 시도</Text>
                </TouchableOpacity>
              </View>
            ) : (
              previewUri ? (
                <Pdf
                  source={{ uri: previewUri, cache: false }}
                  style={{ flex: 1 }}
                  trustAllCerts={false}
                  onError={() => setHasError(true)}
                  renderActivityIndicator={() => (
                    <View className="flex-1 justify-center items-center">
                      <ActivityIndicator size="large" color="#2563eb" />
                      <Text className="mt-4 text-gray-500">PDF 로딩 중...</Text>
                    </View>
                  )}
                />
              ) : (
                <View className="flex-1 justify-center items-center">
                  <ActivityIndicator size="large" color="#2563eb" />
                  <Text className="mt-4 text-gray-500">PDF 로딩 중...</Text>
                </View>
              )
            )}

            <TouchableOpacity
              className="absolute bottom-6 right-6 bg-blue-600 w-14 h-14 rounded-full items-center justify-center shadow-lg"
              onPress={() => openPDF(shuttle.file_url!)}
              disabled={isDownloading}
            >
              {isDownloading ? <ActivityIndicator color="white" /> : <Download size={24} color="white" />}
            </TouchableOpacity>
          </View>
        </View>
      )}
    </AppScreenLayout>
  );
}

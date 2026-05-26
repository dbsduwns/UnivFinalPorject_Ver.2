import { Text, View, Platform, TouchableOpacity, ActivityIndicator } from "react-native";
import { WebView } from "react-native-webview";
import { useState } from "react";

import { useQuery } from "@tanstack/react-query";
import { getShuttles } from "@/features/shuttle/api/shuttle";
import { getCurrentSemester } from "@/features/shuttle/utils/semester";
import { AppScreenLayout } from "@/components/AppScreenLayout";
import { FileText, Download, AlertCircle } from "lucide-react-native";
import { API_BASE_URL } from "@/constants/config";

import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

export default function ShuttleScreen() {
  const semester = getCurrentSemester();
  const [isDownloading, setIsDownloading] = useState(false);
  const [hasError, setHasError] = useState(false);

  const { data: shuttles = [], isLoading, refetch } = useQuery({
    queryKey: ["shuttles", semester],
    queryFn: () => getShuttles({ semester }),
  });

  const shuttle = shuttles[0];

  const getFullUrl = (url: string) => {
    if (!url) return "";
    if (url.startsWith("http")) return url;
    return `${API_BASE_URL}${url}`;
  };

  const openPDF = async (pdfUrl: string) => {
    if (!pdfUrl) return;
    
    const fullUrl = getFullUrl(pdfUrl);
    
    try {
      setIsDownloading(true);
      const fileName = `shuttle_schedule_${Date.now()}.pdf`;
      
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
      console.error("PDF 열기 실패:", error);
      alert("PDF를 불러오는 중 오류가 발생했습니다.");
    } finally {
      setIsDownloading(false);
    }
  };

  const getPdfUri = (url: string) => {
    const fullUrl = getFullUrl(url);
    if (Platform.OS === 'android') {
      // 안드로이드는 Google Docs Viewer 사용 (직접 PDF 보기가 불안정한 경우가 많음)
      return `https://docs.google.com/gview?embedded=true&url=${encodeURIComponent(fullUrl)}`;
    }
    // iOS는 WKWebView가 PDF를 직접 지원함
    return fullUrl;
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
                <Text className="mt-4 text-lg font-bold text-gray-900 text-center">미리보기를 불러올 수 없습니다</Text>
                <Text className="mt-2 text-gray-500 text-center">
                  {Platform.OS === 'android' && API_BASE_URL.includes('127.0.0.1') 
                    ? "로컬 환경(127.0.0.1)에서는 구글 뷰어가\n파일에 접근할 수 없습니다.\n아래 버튼을 눌러 직접 열어주세요."
                    : "네트워크 상태를 확인하거나 아래 버튼을 눌러\n직접 파일을 열어주세요."}
                </Text>
                <TouchableOpacity 
                  onPress={() => setHasError(false)}
                  className="mt-6 px-6 py-3 bg-gray-100 rounded-xl"
                >
                  <Text className="text-gray-700 font-medium">다시 시도</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <WebView
                source={{ uri: getPdfUri(shuttle.file_url!) }}
                style={{ flex: 1 }}
                scalesPageToFit={true}
                startInLoadingState={true}
                originWhitelist={['*']}
                mixedContentMode="always"
                onError={() => setHasError(true)}
                renderLoading={() => (
                  <View className="absolute inset-0 justify-center items-center bg-white">
                    <ActivityIndicator size="large" color="#2563eb" />
                    <Text className="mt-4 text-gray-500">PDF 로딩 중...</Text>
                  </View>
                )}
              />
            )}
            
            {/* 우측 하단 플로팅 다운로드/공유 버튼 */}
            <TouchableOpacity 
              className="absolute bottom-6 right-6 bg-blue-600 w-14 h-14 rounded-full items-center justify-center shadow-lg"
              onPress={() => openPDF(shuttle.file_url!)}
              disabled={isDownloading}
            >
              {isDownloading ? (
                <ActivityIndicator color="white" />
              ) : (
                <Download size={24} color="white" />
              )}
            </TouchableOpacity>
          </View>
        </View>
      )}
    </AppScreenLayout>
  );
}

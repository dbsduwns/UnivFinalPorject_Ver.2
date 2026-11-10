import { ActivityIndicator, Text, View } from "react-native";
import { useEffect, useState } from "react";

import Pdf from "react-native-pdf";
import * as FileSystem from "expo-file-system/legacy";

type PdfPreviewProps = {
  sourceUrl: string | null;
};

export default function PdfPreview({ sourceUrl }: PdfPreviewProps) {
  const [previewUri, setPreviewUri] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    setPreviewUri(null);
    setHasError(false);

    if (!sourceUrl || !FileSystem.cacheDirectory) {
      if (sourceUrl) setHasError(true);
      return () => {
        isCurrent = false;
      };
    }

    const localUri = `${FileSystem.cacheDirectory}shuttle_preview_${Date.now()}.pdf`;
    FileSystem.downloadAsync(sourceUrl, localUri)
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
  }, [sourceUrl]);

  if (hasError) {
    return (
      <Text className="flex-1 px-5 text-center text-gray-500">
        미리보기를 불러오지 못했습니다. 아래 PDF 열기를 이용해주세요.
      </Text>
    );
  }

  if (!previewUri) {
    return (
      <View className="flex-1 items-center justify-center">
        <ActivityIndicator size="large" color="#2563eb" />
        <Text className="mt-3 text-gray-500">PDF 미리보기 준비 중...</Text>
      </View>
    );
  }

  return (
    <View className="w-full flex-1">
      <Pdf
        source={{ uri: previewUri, cache: false }}
        style={{ flex: 1 }}
        trustAllCerts={false}
        onError={() => setHasError(true)}
      />
    </View>
  );
}

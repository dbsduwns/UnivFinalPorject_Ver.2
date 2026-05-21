import { Text, View, Platform } from "react-native";
import { WebView } from "react-native-webview";

import { AppScrollContent } from "@/components/AppScrollContent";
import { useQuery } from "@tanstack/react-query";
import { getShuttles } from "@/features/shuttle/shuttle";
import { getCurrentSemester } from "@/features/shuttle/utils/semester";
import { AppScreenLayout } from "@/components/AppScreenLayout";

export default function ShuttleScreen() {

  const semester = getCurrentSemester();

  const { data: shuttles = [], isLoading } = useQuery({
    queryKey: ["shuttles", semester],
    queryFn: () => getShuttles({semester}),
  });

  const shuttle = shuttles[0];

  const getPdfUri = (url: string) => {
    if (Platform.OS === 'android') {
      return `https://docs.google.com/gview?embedded=true&url=${encodeURIComponent(url)}`;
    }
    return url;
  };

  return (
    <AppScreenLayout>
      {isLoading ? (
        <Text>셔틀 시간표를 불러오는 중...</Text>
      ) : (!shuttle ? (
        <Text>등록된 셔틀 시간표가 없습니다.</Text>
      ) : (
      <View style={{ flex: 1 }}>
        <View style={{ flex: 1, overflow: "hidden" }}>
          <WebView
            source={{ uri: getPdfUri(shuttle.file_url! )}}
            style={{ flex: 1 }}
            scalesPageToFit={true}
            startInLoadingState={true}
            originWhitelist={['*']}
            mixedContentMode="always"
          />
        </View>
      </View>
      )) }
    </AppScreenLayout>
  );
}

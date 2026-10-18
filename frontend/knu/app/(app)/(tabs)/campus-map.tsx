import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Dimensions,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { GoogleMaps } from "expo-maps";
import { useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { Bus, Footprints, MapPinned, Navigation } from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import { getTodayCommute } from "@/features/commute/api/commute";
import type { RouteCoordinate, RouteStep } from "@/features/commute/api/types";

const CAMPUS_CENTER: RouteCoordinate = {
  latitude: 37.2757,
  longitude: 127.1325,
};

const CAMPUS_LOCATIONS = [
  { name: "본관", latitude: 37.276089, longitude: 127.133217 },
  { name: "샬롬관", latitude: 37.274935, longitude: 127.13004 },
  { name: "경천관", latitude: 37.276534, longitude: 127.133904 },
  { name: "우원관", latitude: 37.275812, longitude: 127.1317 },
  { name: "인사관", latitude: 37.275355, longitude: 127.130796 },
  { name: "예술관", latitude: 37.276066, longitude: 127.130845 },
  { name: "도서관", latitude: 37.276518, longitude: 127.13216 },
  { name: "승리관", latitude: 37.274474, longitude: 127.132467 },
  { name: "교육관", latitude: 37.275335, longitude: 127.133302 },
  { name: "천은관", latitude: 37.275759, longitude: 127.134297 },
  { name: "후생관", latitude: 37.276921, longitude: 127.133535 },
  { name: "이공관", latitude: 37.277086, longitude: 127.134147 },
  { name: "심전2관", latitude: 37.278582, longitude: 127.133742 },
  { name: "심전1관", latitude: 37.278044, longitude: 127.134401 },
];

type MapMode = "campus" | "commute";

function getStepColor(mode: string) {
  switch (mode) {
    case "WALK":
      return "#64748B";
    case "TRANSIT":
      return "#13708D";
    default:
      return "#94A3B8";
  }
}

function getStepLabel(step: RouteStep) {
  if (step.travel_mode === "WALK") {
    return step.instruction ?? `도보 ${step.duration_minutes}분`;
  }

  const line = step.transit_line_name
    ? `${step.transit_line_name} 탑승`
    : "대중교통 탑승";
  const stops = [step.departure_stop_name, step.arrival_stop_name]
    .filter(Boolean)
    .join(" → ");

  return [line, stops].filter(Boolean).join(" · ");
}

// 전체 경로의 경계와 화면 크기를 이용해 중앙 좌표와 줌을 계산한다.
function getRouteCamera(routePath: RouteCoordinate[]) {
  if (routePath.length === 0) {
    return { coordinates: CAMPUS_CENTER, zoom: 16 };
  }

  const latitudes = routePath.map(({ latitude }) => latitude);
  const longitudes = routePath.map(({ longitude }) => longitude);
  const minLatitude = Math.min(...latitudes);
  const maxLatitude = Math.max(...latitudes);
  const minLongitude = Math.min(...longitudes);
  const maxLongitude = Math.max(...longitudes);
  const latitudeDelta = Math.max(maxLatitude - minLatitude, 0.001);
  const longitudeDelta = Math.max(maxLongitude - minLongitude, 0.001);
  const { width, height } = Dimensions.get("window");

  const longitudeZoom = Math.log2(
    (360 * width * 0.78) / (longitudeDelta * 256),
  );
  const latitudeZoom = Math.log2(
    (170 * height * 0.55) / (latitudeDelta * 256),
  );

  return {
    coordinates: {
      latitude: (minLatitude + maxLatitude) / 2,
      longitude: (minLongitude + maxLongitude) / 2,
    },
    zoom: Math.max(
      4,
      Math.min(17, Math.floor(Math.min(latitudeZoom, longitudeZoom))),
    ),
  };
}

export default function CampusMapScreen() {
  const { mode } = useLocalSearchParams<{ mode?: string }>();
  const [mapMode, setMapMode] = useState<MapMode>(
    mode === "commute" ? "commute" : "campus",
  );
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const mapRef = useRef<GoogleMaps.MapView>(null);

  // 등교 모드에서만 백엔드의 Google Routes 결과를 조회한다.
  const {
    data: commute,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["commute", "today"],
    queryFn: getTodayCommute,
    enabled: mapMode === "commute",
    staleTime: 60_000,
    retry: false,
  });

  const route = commute?.recommended_route;
  const routePath = useMemo(() => route?.route_path ?? [], [route?.route_path]);
  const routeSteps = useMemo(
    () => route?.route_steps ?? [],
    [route?.route_steps],
  );

  // 단계별 좌표가 있으면 도보와 대중교통을 서로 다른 색상으로 그린다.
  const stepPolylines = useMemo(
    () =>
      routeSteps
        .filter((step) => step.route_path.length > 1)
        .map((step, index) => ({
          id: `commute-step-${index}`,
          coordinates: step.route_path,
          color: getStepColor(step.travel_mode),
          width: step.travel_mode === "WALK" ? 5 : 8,
        })),
    [routeSteps],
  );

  // 단계별 선이 없는 응답에서는 전체 경로 선을 안전한 대체값으로 사용한다.
  const routePolylines = useMemo(
    () =>
      routePath.length > 1
        ? [
            {
              id: "commute-route",
              coordinates: routePath,
              color: "#13708D",
              width: 8,
            },
          ]
        : [],
    [routePath],
  );

  const routeCamera = useMemo(() => getRouteCamera(routePath), [routePath]);

  // 지도와 모든 경로 좌표가 준비된 뒤 전체 경로가 보이도록 카메라를 이동한다.
  useEffect(() => {
    if (!isMapLoaded) return;

    const camera =
      mapMode === "commute" && routePath.length > 0
        ? routeCamera
        : { coordinates: CAMPUS_CENTER, zoom: 16 };

    mapRef.current?.setCameraPosition({ ...camera, duration: 650 });
  }, [isMapLoaded, mapMode, routeCamera, routePath.length]);

  const markers =
    mapMode === "commute" && routePath.length > 1
      ? [
          {
            id: "origin",
            coordinates: routePath[0],
            title: "출발",
            showCallout: true,
          },
          {
            id: "destination",
            coordinates: routePath[routePath.length - 1],
            title: commute?.destination?.destination_name ?? "도착",
            showCallout: true,
          },
        ]
      : CAMPUS_LOCATIONS.map((location) => ({
          id: `campus-${location.name}`,
          coordinates: location,
          title: location.name,
          showCallout: true,
        }));

  if (Platform.OS !== "android") {
    return (
      <AppScreenLayout>
        <View style={styles.centeredMessage}>
          <Text style={styles.messageTitle}>Google 지도는 Android에서 지원됩니다.</Text>
          <Text style={styles.messageBody}>iOS 지도 지원은 별도 구현이 필요합니다.</Text>
        </View>
      </AppScreenLayout>
    );
  }

  return (
    <AppScreenLayout>
      <View style={styles.container}>
        <GoogleMaps.View
          ref={mapRef}
          style={StyleSheet.absoluteFill}
          cameraPosition={{ coordinates: CAMPUS_CENTER, zoom: 16 }}
          markers={markers}
          polylines={stepPolylines.length > 0 ? stepPolylines : routePolylines}
          uiSettings={{
            zoomControlsEnabled: true,
            myLocationButtonEnabled: false,
          }}
          onMapLoaded={() => setIsMapLoaded(true)}
        />

        {/* 캠퍼스 안내와 등교 경로를 한 지도에서 전환한다. */}
        <View style={styles.modeSelector}>
          <TouchableOpacity
            style={[
              styles.modeButton,
              mapMode === "campus" && styles.activeModeButton,
            ]}
            onPress={() => setMapMode("campus")}
          >
            <MapPinned
              size={17}
              color={mapMode === "campus" ? "#FFFFFF" : "#475569"}
            />
            <Text
              style={[
                styles.modeButtonText,
                mapMode === "campus" && styles.activeModeButtonText,
              ]}
            >
              캠퍼스 안내
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.modeButton,
              mapMode === "commute" && styles.activeModeButton,
            ]}
            onPress={() => setMapMode("commute")}
          >
            <Navigation
              size={17}
              color={mapMode === "commute" ? "#FFFFFF" : "#475569"}
            />
            <Text
              style={[
                styles.modeButtonText,
                mapMode === "commute" && styles.activeModeButtonText,
              ]}
            >
              등교 경로
            </Text>
          </TouchableOpacity>
        </View>

        {/* 경로 조회 상태와 실패 원인을 지도 위에서 바로 안내한다. */}
        {mapMode === "commute" && isLoading && (
          <View style={styles.statusCard}>
            <ActivityIndicator color="#13708D" />
            <Text style={styles.statusText}>등교 경로를 불러오고 있어요</Text>
          </View>
        )}
        {mapMode === "commute" &&
          (isError || commute?.status !== "ready") &&
          !isLoading && (
            <View style={styles.statusCard}>
              <Text style={styles.statusText}>
                {commute?.message ?? "등교 경로를 불러오지 못했습니다."}
              </Text>
              <TouchableOpacity
                style={styles.retryButton}
                onPress={() => void refetch()}
              >
                <Text style={styles.retryButtonText}>다시 시도</Text>
              </TouchableOpacity>
            </View>
          )}

        {/* 카카오 드로어에서 필요했던 경로 요약과 단계별 안내만 유지한다. */}
        {mapMode === "commute" && route && (
          <View style={styles.routePanel}>
            <View style={styles.routeHeader}>
              <View style={styles.routeTitleWrap}>
                <Text style={styles.routeTitle}>
                  {route.route_name ?? "추천 대중교통 경로"}
                </Text>
                <Text style={styles.routeSummary}>
                  총 {route.duration_minutes}분 · 도보 {route.walking_minutes}분 · 환승 {route.transfer_count}회
                </Text>
              </View>
              <Bus size={22} color="#13708D" />
            </View>

            {routeSteps.length > 0 && (
              <ScrollView
                style={styles.stepList}
                contentContainerStyle={styles.stepListContent}
                showsVerticalScrollIndicator={false}
              >
                {routeSteps.map((step, index) => (
                  <View key={`${step.travel_mode}-${index}`} style={styles.stepRow}>
                    <View
                      style={[
                        styles.stepIcon,
                        { backgroundColor: `${getStepColor(step.travel_mode)}18` },
                      ]}
                    >
                      {step.travel_mode === "WALK" ? (
                        <Footprints
                          size={17}
                          color={getStepColor(step.travel_mode)}
                        />
                      ) : (
                        <Bus size={17} color={getStepColor(step.travel_mode)} />
                      )}
                    </View>
                    <View style={styles.stepTextWrap}>
                      <Text style={styles.stepText}>{getStepLabel(step)}</Text>
                      <Text style={styles.stepMeta}>
                        {step.duration_minutes}분
                        {step.distance_meters > 0
                          ? ` · ${step.distance_meters}m`
                          : ""}
                      </Text>
                    </View>
                  </View>
                ))}
              </ScrollView>
            )}
          </View>
        )}
      </View>
    </AppScreenLayout>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centeredMessage: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  messageTitle: { fontSize: 17, fontWeight: "700", color: "#0F172A" },
  messageBody: { marginTop: 8, fontSize: 13, color: "#64748B" },
  modeSelector: {
    position: "absolute",
    top: 16,
    left: 16,
    right: 16,
    flexDirection: "row",
    padding: 4,
    borderRadius: 16,
    backgroundColor: "#FFFFFF",
    elevation: 6,
    shadowColor: "#0F172A",
    shadowOpacity: 0.14,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  modeButton: {
    flex: 1,
    height: 42,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    borderRadius: 12,
  },
  activeModeButton: { backgroundColor: "#13708D" },
  modeButtonText: { fontSize: 13, fontWeight: "700", color: "#475569" },
  activeModeButtonText: { color: "#FFFFFF" },
  statusCard: {
    position: "absolute",
    top: 76,
    left: 16,
    right: 16,
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingHorizontal: 16,
    borderRadius: 14,
    backgroundColor: "#FFFFFF",
    elevation: 5,
  },
  statusText: { flexShrink: 1, fontSize: 13, color: "#475569" },
  retryButton: {
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 9,
    backgroundColor: "#EAF8FC",
  },
  retryButtonText: { fontSize: 12, fontWeight: "700", color: "#13708D" },
  routePanel: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 18,
    maxHeight: 270,
    padding: 18,
    borderRadius: 20,
    backgroundColor: "#FFFFFF",
    elevation: 8,
    shadowColor: "#0F172A",
    shadowOpacity: 0.18,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 5 },
  },
  routeHeader: { flexDirection: "row", alignItems: "center" },
  routeTitleWrap: { flex: 1, paddingRight: 12 },
  routeTitle: { fontSize: 16, fontWeight: "700", color: "#0F172A" },
  routeSummary: { marginTop: 5, fontSize: 12, color: "#64748B" },
  stepList: { marginTop: 14 },
  stepListContent: { gap: 12, paddingBottom: 2 },
  stepRow: { flexDirection: "row", alignItems: "center" },
  stepIcon: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 17,
  },
  stepTextWrap: { flex: 1, marginLeft: 10 },
  stepText: { fontSize: 13, fontWeight: "600", color: "#334155" },
  stepMeta: { marginTop: 3, fontSize: 11, color: "#94A3B8" },
});

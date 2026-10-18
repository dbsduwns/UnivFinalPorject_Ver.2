import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Dimensions,
  PanResponder,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { GoogleMaps } from "expo-maps";
import { useImage } from "expo-image";
import { useLocalSearchParams } from "expo-router";
import { useIsFocused } from "@react-navigation/native";
import { useQuery } from "@tanstack/react-query";
import {
  Bus,
  ChevronLeft,
  ChevronUp,
  Footprints,
  MapPinned,
  Navigation,
  TrainFront,
} from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import {
  getLiveBusPositions,
  getTodayCommute,
} from "@/features/commute/api/commute";
import type {
  LiveBusPosition,
  RouteCoordinate,
  RouteStep,
} from "@/features/commute/api/types";

const GOOGLE_MAP_ID = process.env.EXPO_PUBLIC_GOOGLE_MAP_ID?.trim();
const { height: SCREEN_HEIGHT } = Dimensions.get("window");
const SHEET_MAX_HEIGHT = Math.min(SCREEN_HEIGHT * 0.7, 620);
const SHEET_MIN_HEIGHT = 112;
const SHEET_COLLAPSED_Y = SHEET_MAX_HEIGHT - SHEET_MIN_HEIGHT;
const SHEET_HALF_Y = SHEET_COLLAPSED_Y * 0.48;
const TRANSIT_FALLBACK_COLORS = ["#13708D", "#7C3AED", "#DC2626", "#D97706"];

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

const ROUTE_CATEGORY_LABELS = {
  google_recommended: "Google 추천",
  fastest: "최단 시간",
  least_walking: "최소 도보",
  fewest_transfers: "최소 환승",
} as const;

function getStepColor(step: RouteStep, index = 0) {
  if (step.travel_mode === "WALK") return "#94A3B8";

  const googleColor = step.transit_line_color?.trim();
  if (
    googleColor &&
    /^#[0-9A-F]{6}$/i.test(googleColor) &&
    googleColor.toUpperCase() !== "#FFFFFF"
  ) {
    return googleColor;
  }

  return TRANSIT_FALLBACK_COLORS[index % TRANSIT_FALLBACK_COLORS.length];
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

function formatRouteTime(value: string | null) {
  return value ? value.slice(0, 5) : "--:--";
}

function isRailStep(step: RouteStep) {
  const vehicleType = step.vehicle_type ?? "";
  return ["SUBWAY", "TRAIN", "RAIL", "LIGHT_RAIL", "TRAM"].some((type) =>
    vehicleType.includes(type),
  );
}

function RouteStepIcon({ step, color, size = 16 }: {
  step: RouteStep;
  color: string;
  size?: number;
}) {
  if (step.travel_mode === "WALK") {
    return <Footprints size={size} color={color} />;
  }
  if (isRailStep(step)) {
    return <TrainFront size={size} color={color} />;
  }
  return <Bus size={size} color={color} />;
}

function getCompactRouteSteps(steps: RouteStep[]) {
  return steps.filter((step, index) => {
    if (index === 0) return true;
    const previous = steps[index - 1];
    return !(
      previous.travel_mode === step.travel_mode &&
      previous.transit_line_name === step.transit_line_name
    );
  });
}

type TimelineItem =
  | { type: "location"; label: string; emphasis?: boolean }
  | { type: "segment"; step: RouteStep; stepIndex: number };

function buildRouteTimeline(
  steps: RouteStep[],
  destinationName: string,
): TimelineItem[] {
  const items: TimelineItem[] = [
    { type: "location", label: "출발지", emphasis: true },
  ];
  let lastLocation = "출발지";

  const addLocation = (label: string | null | undefined) => {
    const normalized = label?.trim();
    if (!normalized || normalized === lastLocation) return;
    items.push({ type: "location", label: normalized });
    lastLocation = normalized;
  };

  steps.forEach((step, stepIndex) => {
    if (step.travel_mode === "TRANSIT") {
      addLocation(step.departure_stop_name);
    }

    items.push({ type: "segment", step, stepIndex });

    if (step.travel_mode === "TRANSIT") {
      addLocation(step.arrival_stop_name);
    }
  });

  if (destinationName !== lastLocation) {
    items.push({ type: "location", label: destinationName, emphasis: true });
  } else {
    const lastItem = items[items.length - 1];
    if (lastItem.type === "location") lastItem.emphasis = true;
  }

  return items;
}

const EARTH_RADIUS_METERS = 6_371_000;

function getCoordinateDistance(
  start: RouteCoordinate,
  end: RouteCoordinate,
) {
  const toRadians = (degree: number) => (degree * Math.PI) / 180;
  const latitudeDelta = toRadians(end.latitude - start.latitude);
  const longitudeDelta = toRadians(end.longitude - start.longitude);
  const startLatitude = toRadians(start.latitude);
  const endLatitude = toRadians(end.latitude);
  const haversine =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(startLatitude) *
      Math.cos(endLatitude) *
      Math.sin(longitudeDelta / 2) ** 2;

  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.sqrt(haversine));
}

function interpolateCoordinate(
  start: RouteCoordinate,
  end: RouteCoordinate,
  ratio: number,
): RouteCoordinate {
  return {
    latitude: start.latitude + (end.latitude - start.latitude) * ratio,
    longitude: start.longitude + (end.longitude - start.longitude) * ratio,
  };
}

// Expo Maps에 dashPattern이 없어 경로를 일정 길이의 선과 공백으로 분할한다.
function buildDashedRouteSegments(
  coordinates: RouteCoordinate[],
  dashMeters = 18,
  gapMeters = 11,
) {
  if (coordinates.length < 2) return [];

  const segments: RouteCoordinate[][] = [];
  let isDrawing = true;
  let patternDistance = 0;
  let currentDash: RouteCoordinate[] = [];

  for (let index = 1; index < coordinates.length; index += 1) {
    let segmentStart = coordinates[index - 1];
    const segmentEnd = coordinates[index];
    let remainingDistance = getCoordinateDistance(segmentStart, segmentEnd);

    while (remainingDistance > 0.01) {
      const targetLength = isDrawing ? dashMeters : gapMeters;
      const availablePatternDistance = targetLength - patternDistance;
      const travelDistance = Math.min(
        remainingDistance,
        availablePatternDistance,
      );
      const nextCoordinate = interpolateCoordinate(
        segmentStart,
        segmentEnd,
        travelDistance / remainingDistance,
      );

      if (isDrawing) {
        if (currentDash.length === 0) currentDash.push(segmentStart);
        currentDash.push(nextCoordinate);
      }

      segmentStart = nextCoordinate;
      remainingDistance -= travelDistance;
      patternDistance += travelDistance;

      if (patternDistance >= targetLength - 0.01) {
        if (isDrawing && currentDash.length > 1) segments.push(currentDash);
        currentDash = [];
        isDrawing = !isDrawing;
        patternDistance = 0;
      }
    }
  }

  if (currentDash.length > 1) segments.push(currentDash);
  return segments;
}

function getRouteProgress(
  routePath: RouteCoordinate[],
  position: RouteCoordinate,
) {
  if (routePath.length < 2) return 0;

  const segmentLengths = routePath.slice(1).map((coordinate, index) =>
    getCoordinateDistance(routePath[index], coordinate),
  );
  const totalDistance = segmentLengths.reduce((sum, length) => sum + length, 0);
  if (totalDistance <= 0) return 0;

  const longitudeScale = Math.cos((position.latitude * Math.PI) / 180);
  let traversedDistance = 0;
  let nearestDistance = Number.POSITIVE_INFINITY;
  let nearestProgress = 0;

  for (let index = 0; index < routePath.length - 1; index += 1) {
    const start = routePath[index];
    const end = routePath[index + 1];
    const startX = start.longitude * longitudeScale;
    const startY = start.latitude;
    const endX = end.longitude * longitudeScale;
    const endY = end.latitude;
    const positionX = position.longitude * longitudeScale;
    const positionY = position.latitude;
    const deltaX = endX - startX;
    const deltaY = endY - startY;
    const lengthSquared = deltaX ** 2 + deltaY ** 2;
    const ratio = lengthSquared > 0
      ? Math.max(
          0,
          Math.min(
            1,
            ((positionX - startX) * deltaX +
              (positionY - startY) * deltaY) /
              lengthSquared,
          ),
        )
      : 0;
    const projected = interpolateCoordinate(start, end, ratio);
    const distance = getCoordinateDistance(position, projected);

    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestProgress =
        (traversedDistance + segmentLengths[index] * ratio) / totalDistance;
    }
    traversedDistance += segmentLengths[index];
  }

  return Math.max(0, Math.min(1, nearestProgress));
}

function selectClosestBus(
  vehicles: LiveBusPosition[],
  boardingCoordinate: RouteCoordinate | undefined,
) {
  if (!boardingCoordinate || vehicles.length === 0) return null;
  return vehicles.reduce((closest, vehicle) => {
    const distance = getCoordinateDistance(boardingCoordinate, vehicle);
    const closestDistance = getCoordinateDistance(boardingCoordinate, closest);
    return distance < closestDistance ? vehicle : closest;
  });
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
  const isFocused = useIsFocused();
  // Android Expo Maps가 안정적으로 처리하는 PNG 브랜드 마커를 로드한다.
  const originMarkerIcon = useImage(
    require("../../../src/assets/images/map-marker-origin.png"),
    { maxWidth: 108, maxHeight: 135 },
  );
  const destinationMarkerIcon = useImage(
    require("../../../src/assets/images/map-marker-destination.png"),
    { maxWidth: 108, maxHeight: 135 },
  );
  const campusMarkerIcon = useImage(
    require("../../../src/assets/images/map-marker-campus.png"),
    { maxWidth: 108, maxHeight: 135 },
  );
  const [mapMode, setMapMode] = useState<MapMode>(
    mode === "commute" ? "commute" : "campus",
  );
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isDetailView, setIsDetailView] = useState(false);
  const [routeFocusRequest, setRouteFocusRequest] = useState(0);
  const mapRef = useRef<GoogleMaps.MapView>(null);
  const liveBusProgressAnimation = useRef(new Animated.Value(0)).current;
  const sheetTranslateY = useRef(new Animated.Value(SHEET_HALF_Y)).current;
  const sheetPositionRef = useRef(SHEET_HALF_Y);
  const dragStartRef = useRef(SHEET_HALF_Y);

  const snapSheet = useCallback((position: number) => {
    const clampedPosition = Math.max(0, Math.min(SHEET_COLLAPSED_Y, position));
    sheetPositionRef.current = clampedPosition;
    Animated.spring(sheetTranslateY, {
      toValue: clampedPosition,
      damping: 22,
      stiffness: 220,
      mass: 0.8,
      useNativeDriver: true,
    }).start();
  }, [sheetTranslateY]);

  const sheetPanResponder = useMemo(
    () => PanResponder.create({
      onMoveShouldSetPanResponder: (_, gesture) => Math.abs(gesture.dy) > 5,
      onPanResponderGrant: () => {
        sheetTranslateY.stopAnimation((value) => {
          dragStartRef.current = value;
          sheetPositionRef.current = value;
        });
      },
      onPanResponderMove: (_, gesture) => {
        const nextPosition = Math.max(
          0,
          Math.min(SHEET_COLLAPSED_Y, dragStartRef.current + gesture.dy),
        );
        sheetPositionRef.current = nextPosition;
        sheetTranslateY.setValue(nextPosition);
      },
      onPanResponderRelease: (_, gesture) => {
        if (gesture.vy < -0.65) {
          snapSheet(0);
          return;
        }
        if (gesture.vy > 0.65) {
          snapSheet(SHEET_COLLAPSED_Y);
          return;
        }

        const snapPoints = [0, SHEET_HALF_Y, SHEET_COLLAPSED_Y];
        const nearest = snapPoints.reduce((current, point) =>
          Math.abs(point - sheetPositionRef.current) <
          Math.abs(current - sheetPositionRef.current)
            ? point
            : current,
        );
        snapSheet(nearest);
      },
      onPanResponderTerminate: () => snapSheet(sheetPositionRef.current),
    }),
    [sheetTranslateY, snapSheet],
  );

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

  const routeOptions = useMemo(
    () => [
      ...(commute?.recommended_route ? [commute.recommended_route] : []),
      ...(commute?.alternatives ?? []),
    ],
    [commute?.alternatives, commute?.recommended_route],
  );
  const route = routeOptions[selectedRouteIndex] ?? commute?.recommended_route;
  const routePath = useMemo(() => route?.route_path ?? [], [route?.route_path]);
  const routeSteps = useMemo(
    () => route?.route_steps ?? [],
    [route?.route_steps],
  );
  const routeTimeline = useMemo(
    () => buildRouteTimeline(
      routeSteps,
      commute?.destination?.destination_name ?? "도착지",
    ),
    [commute?.destination?.destination_name, routeSteps],
  );
  const liveBusStep = useMemo(
    () => routeSteps
      .map((step, stepIndex) => ({ step, stepIndex }))
      .find(({ step }) =>
        step.travel_mode === "TRANSIT" &&
        Boolean(step.tago_city_code && step.tago_route_id),
      ) ?? null,
    [routeSteps],
  );
  const liveBusPollingEnabled = Boolean(
    isFocused &&
    mapMode === "commute" &&
    isDetailView &&
    liveBusStep?.step.tago_city_code &&
    liveBusStep.step.tago_route_id,
  );
  const { data: liveBusPositions, isFetching: isLiveBusFetching } = useQuery({
    queryKey: [
      "commute",
      "live-buses",
      liveBusStep?.step.tago_city_code,
      liveBusStep?.step.tago_route_id,
    ],
    queryFn: () => {
      const cityCode = liveBusStep?.step.tago_city_code;
      const routeId = liveBusStep?.step.tago_route_id;
      if (!cityCode || !routeId) {
        throw new Error("실시간 버스 조회에 필요한 노선 정보가 없습니다.");
      }
      return getLiveBusPositions(cityCode, routeId);
    },
    enabled: liveBusPollingEnabled,
    staleTime: 15_000,
    refetchInterval: liveBusPollingEnabled ? 15_000 : false,
    refetchIntervalInBackground: false,
    retry: false,
  });
  const liveBus = useMemo(
    () => selectClosestBus(
      liveBusPositions?.vehicles ?? [],
      liveBusStep?.step.route_path[0],
    ),
    [liveBusPositions?.vehicles, liveBusStep?.step.route_path],
  );
  const liveBusProgress = useMemo(
    () => liveBus && liveBusStep
      ? getRouteProgress(liveBusStep.step.route_path, liveBus)
      : 0,
    [liveBus, liveBusStep],
  );

  useEffect(() => {
    if (!liveBus) {
      liveBusProgressAnimation.setValue(0);
      return;
    }
    Animated.timing(liveBusProgressAnimation, {
      toValue: liveBusProgress,
      duration: 700,
      useNativeDriver: false,
    }).start();
  }, [liveBus, liveBusProgress, liveBusProgressAnimation]);

  // 단계별 좌표가 있으면 도보와 대중교통을 서로 다른 색상으로 그린다.
  const stepPolylines = useMemo(
    () =>
      routeSteps
        .filter((step) => step.route_path.length > 1)
        .flatMap((step, index) => {
          const color = getStepColor(step, index);

          if (step.travel_mode === "WALK") {
            return buildDashedRouteSegments(step.route_path).map(
              (coordinates, dashIndex) => ({
                id: `commute-step-${index}-dash-${dashIndex}`,
                coordinates,
                color,
                width: 7.5,
                geodesic: true,
              }),
            );
          }

          return [{
            id: `commute-step-${index}`,
            coordinates: step.route_path,
            color,
            width: 12,
            geodesic: true,
          }];
        }),
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
              width: 7.5,
              geodesic: true,
            },
          ]
        : [],
    [routePath],
  );

  const routeCamera = useMemo(() => getRouteCamera(routePath), [routePath]);

  // 새로운 등교 계산 결과가 도착하면 Google 추천 경로를 기본 선택한다.
  useEffect(() => {
    setSelectedRouteIndex(0);
    setIsDetailView(false);
    snapSheet(SHEET_HALF_Y);
  }, [commute?.calculated_at, snapSheet]);

  const openRouteDetail = (index: number) => {
    setSelectedRouteIndex(index);
    setIsDetailView(true);
    setRouteFocusRequest((request) => request + 1);
    // 선택한 경로를 지도에서 확인할 수 있도록 상세 화면은 유지한 채 시트를 접는다.
    snapSheet(SHEET_COLLAPSED_Y);
  };

  // 지도와 모든 경로 좌표가 준비된 뒤 전체 경로가 보이도록 카메라를 이동한다.
  useEffect(() => {
    if (!isMapLoaded) return;

    const camera =
      mapMode === "commute" && routePath.length > 0
        ? routeCamera
        : { coordinates: CAMPUS_CENTER, zoom: 16 };

    mapRef.current?.setCameraPosition({ ...camera, duration: 1 });
  }, [
    isMapLoaded,
    mapMode,
    routeCamera,
    routeFocusRequest,
    routePath.length,
  ]);

  const markers =
    mapMode === "commute" && routePath.length > 1
      ? [
          {
            id: "origin",
            coordinates: routePath[0],
            title: "출발",
            icon: originMarkerIcon ?? undefined,
            anchor: { x: 0.5, y: 1 },
            zIndex: 10,
            showCallout: true,
          },
          {
            id: "destination",
            coordinates: routePath[routePath.length - 1],
            title: commute?.destination?.destination_name ?? "도착",
            icon: destinationMarkerIcon ?? undefined,
            anchor: { x: 0.5, y: 1 },
            zIndex: 10,
            showCallout: true,
          },
        ]
      : CAMPUS_LOCATIONS.map((location) => ({
          id: `campus-${location.name}`,
          coordinates: location,
          title: location.name,
          icon: campusMarkerIcon ?? undefined,
          anchor: { x: 0.5, y: 1 },
          zIndex: 1,
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
          mapOptions={{
            mapId: GOOGLE_MAP_ID,
          }}
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

        {/* 드래그로 최소·중간·최대 높이를 오가는 경로 안내 Bottom Sheet */}
        {mapMode === "commute" && route && (
          <Animated.View
            style={[
              styles.bottomSheet,
              { transform: [{ translateY: sheetTranslateY }] },
            ]}
          >
            <View style={styles.sheetHandleArea} {...sheetPanResponder.panHandlers}>
              <View style={styles.sheetHandle} />
              <TouchableOpacity
                style={styles.sheetTitleRow}
                activeOpacity={0.7}
                onPress={() => snapSheet(
                  sheetPositionRef.current > SHEET_HALF_Y ? 0 : SHEET_COLLAPSED_Y,
                )}
              >
                <View>
                  <Text style={styles.sheetEyebrow}>등교 경로</Text>
                  <Text style={styles.sheetTitle}>
                    {isDetailView ? "상세 이동 안내" : `${routeOptions.length}개 경로 비교`}
                  </Text>
                </View>
                <ChevronUp size={22} color="#64748B" />
              </TouchableOpacity>
            </View>

            {!isDetailView ? (
              <ScrollView
                style={styles.sheetContent}
                contentContainerStyle={styles.routeCardList}
                showsVerticalScrollIndicator={false}
              >
                {routeOptions.map((option, index) => {
                  const category = option.route_category ?? "google_recommended";
                  const compactSteps = getCompactRouteSteps(option.route_steps ?? []);

                  return (
                    <TouchableOpacity
                      key={`${category}-${index}`}
                      style={styles.routeCard}
                      activeOpacity={0.75}
                      onPress={() => openRouteDetail(index)}
                    >
                      <View style={styles.routeCardTopRow}>
                        <View style={styles.routeCategoryBadge}>
                          <Text style={styles.routeCategoryText}>
                            {ROUTE_CATEGORY_LABELS[category]}
                          </Text>
                        </View>
                        <Text style={styles.routeCardTime}>
                          {option.duration_minutes}
                          <Text style={styles.routeCardTimeUnit}>분</Text>
                        </Text>
                      </View>

                      <View style={styles.compactRouteRow}>
                        {compactSteps.map((step, stepIndex) => {
                          const color = getStepColor(step, stepIndex);
                          return (
                            <View
                              key={`${step.travel_mode}-${step.transit_line_name}-${stepIndex}`}
                              style={styles.compactStepWrap}
                            >
                              {stepIndex > 0 && <View style={styles.compactConnector} />}
                              <View style={[styles.compactStep, { borderColor: color }]}>
                                <RouteStepIcon step={step} color={color} size={14} />
                                {step.transit_line_name && (
                                  <Text style={[styles.compactStepText, { color }]}>
                                    {step.transit_line_name}
                                  </Text>
                                )}
                              </View>
                            </View>
                          );
                        })}
                      </View>

                      <View style={styles.routeCardBottomRow}>
                        <Text style={styles.routeCardClock}>
                          {formatRouteTime(option.departure_time)} - {formatRouteTime(option.arrival_time)}
                        </Text>
                        <Text style={styles.routeCardMeta}>
                          도보 {option.walking_minutes}분 · 환승 {option.transfer_count}회
                        </Text>
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            ) : (
              <View style={styles.detailContainer}>
                <TouchableOpacity
                  style={styles.detailBackButton}
                  onPress={() => setIsDetailView(false)}
                >
                  <ChevronLeft size={19} color="#13708D" />
                  <Text style={styles.detailBackText}>경로 목록</Text>
                </TouchableOpacity>

                <View style={styles.detailSummaryCard}>
                  <View>
                    <Text style={styles.detailCategory}>
                      {ROUTE_CATEGORY_LABELS[
                        route.route_category ?? "google_recommended"
                      ]}
                    </Text>
                    <Text style={styles.detailRouteName}>
                      {route.route_name ?? "추천 대중교통 경로"}
                    </Text>
                  </View>
                  <View style={styles.detailDurationWrap}>
                    <Text style={styles.detailDuration}>{route.duration_minutes}분</Text>
                    <Text style={styles.detailClock}>
                      {formatRouteTime(route.departure_time)} - {formatRouteTime(route.arrival_time)}
                    </Text>
                  </View>
                </View>

                <ScrollView
                  style={styles.timelineScroll}
                  contentContainerStyle={styles.timelineContent}
                  showsVerticalScrollIndicator={false}
                >
                  {routeTimeline.map((item, index) => {
                    if (item.type === "location") {
                      return (
                        <View key={`location-${item.label}-${index}`} style={styles.locationRow}>
                          <View style={styles.timelineLeftColumn}>
                            <View style={[
                              styles.locationDot,
                              item.emphasis && styles.emphasisLocationDot,
                            ]} />
                          </View>
                          <View style={styles.locationTextWrap}>
                            <Text style={[
                              styles.locationText,
                              item.emphasis && styles.emphasisLocationText,
                            ]}>
                              {item.label}
                            </Text>
                            {index === 0 && (
                              <Text style={styles.locationTime}>
                                {formatRouteTime(route.departure_time)} 출발
                              </Text>
                            )}
                            {index === routeTimeline.length - 1 && (
                              <Text style={styles.locationTime}>
                                {formatRouteTime(route.arrival_time)} 도착
                              </Text>
                            )}
                          </View>
                        </View>
                      );
                    }

                    const color = getStepColor(item.step, item.stepIndex);
                    const isLiveBusStep =
                      liveBusStep?.stepIndex === item.stepIndex;
                    return (
                      <View key={`segment-${item.stepIndex}-${index}`} style={styles.segmentRow}>
                        <View style={styles.timelineLeftColumn}>
                          <View style={[styles.segmentLine, { backgroundColor: color }]} />
                          <View style={[styles.segmentIcon, { backgroundColor: color }]}>
                            <RouteStepIcon step={item.step} color="#FFFFFF" size={14} />
                          </View>
                          {isLiveBusStep && liveBus && (
                            <Animated.View
                              style={[
                                styles.liveBusMarker,
                                {
                                  borderColor: color,
                                  top: liveBusProgressAnimation.interpolate({
                                    inputRange: [0, 1],
                                    outputRange: [31, 49],
                                  }),
                                },
                              ]}
                            >
                              <Bus size={12} color={color} />
                            </Animated.View>
                          )}
                        </View>
                        <View style={styles.segmentContent}>
                          <Text style={styles.segmentTitle}>{getStepLabel(item.step)}</Text>
                          <Text style={styles.segmentMeta}>
                            {item.step.duration_minutes}분
                            {item.step.distance_meters > 0
                              ? ` · ${item.step.distance_meters}m`
                              : ""}
                          </Text>
                          {isLiveBusStep && (
                            <Text style={styles.liveBusText}>
                              {liveBus
                                ? `실시간 · ${liveBus.current_stop_name ?? liveBus.vehicle_number}`
                                : isLiveBusFetching
                                  ? "실시간 버스 위치 확인 중"
                                  : "실시간 버스 위치 정보 없음"}
                            </Text>
                          )}
                        </View>
                      </View>
                    );
                  })}
                </ScrollView>
              </View>
            )}
          </Animated.View>
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
  bottomSheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: SHEET_MAX_HEIGHT,
    borderTopLeftRadius: 26,
    borderTopRightRadius: 26,
    backgroundColor: "#FFFFFF",
    elevation: 14,
    shadowColor: "#0F172A",
    shadowOpacity: 0.22,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: -5 },
    overflow: "hidden",
  },
  sheetHandleArea: { paddingTop: 10, paddingHorizontal: 20, paddingBottom: 12 },
  sheetHandle: {
    alignSelf: "center",
    width: 44,
    height: 5,
    marginBottom: 10,
    borderRadius: 3,
    backgroundColor: "#CBD5E1",
  },
  sheetTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sheetEyebrow: { fontSize: 11, fontWeight: "700", color: "#13708D" },
  sheetTitle: { marginTop: 2, fontSize: 18, fontWeight: "800", color: "#0F172A" },
  sheetContent: { flex: 1 },
  routeCardList: { gap: 12, paddingHorizontal: 16, paddingBottom: 28 },
  routeCard: {
    padding: 16,
    borderWidth: 1,
    borderColor: "#E2E8F0",
    borderRadius: 18,
    backgroundColor: "#FFFFFF",
  },
  routeCardTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  routeCategoryBadge: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: "#EAF8FC",
  },
  routeCategoryText: { fontSize: 11, fontWeight: "800", color: "#13708D" },
  routeCardTime: { fontSize: 24, fontWeight: "800", color: "#0F172A" },
  routeCardTimeUnit: { fontSize: 13, fontWeight: "700", color: "#475569" },
  compactRouteRow: {
    minHeight: 42,
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    marginTop: 10,
  },
  compactStepWrap: { flexDirection: "row", alignItems: "center" },
  compactConnector: { width: 16, height: 2, backgroundColor: "#CBD5E1" },
  compactStep: {
    minHeight: 30,
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 8,
    borderWidth: 1.5,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
  },
  compactStepText: { maxWidth: 74, fontSize: 10, fontWeight: "800" },
  routeCardBottomRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 10,
    paddingTop: 11,
    borderTopWidth: 1,
    borderTopColor: "#F1F5F9",
  },
  routeCardClock: { fontSize: 13, fontWeight: "700", color: "#334155" },
  routeCardMeta: { fontSize: 11, color: "#64748B" },
  detailContainer: { flex: 1, paddingHorizontal: 18 },
  detailBackButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    marginBottom: 10,
  },
  detailBackText: { fontSize: 13, fontWeight: "700", color: "#13708D" },
  detailSummaryCard: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 15,
    borderRadius: 16,
    backgroundColor: "#F8FAFC",
  },
  detailCategory: { fontSize: 11, fontWeight: "800", color: "#13708D" },
  detailRouteName: {
    maxWidth: 200,
    marginTop: 4,
    fontSize: 15,
    fontWeight: "800",
    color: "#0F172A",
  },
  detailDurationWrap: { alignItems: "flex-end" },
  detailDuration: { fontSize: 20, fontWeight: "800", color: "#0F172A" },
  detailClock: { marginTop: 3, fontSize: 11, color: "#64748B" },
  timelineScroll: { flex: 1, marginTop: 12 },
  timelineContent: { paddingBottom: 30 },
  locationRow: { minHeight: 46, flexDirection: "row", alignItems: "flex-start" },
  timelineLeftColumn: { width: 38, alignItems: "center", alignSelf: "stretch" },
  locationDot: {
    width: 12,
    height: 12,
    marginTop: 5,
    borderWidth: 3,
    borderColor: "#94A3B8",
    borderRadius: 6,
    backgroundColor: "#FFFFFF",
    zIndex: 2,
  },
  emphasisLocationDot: { borderColor: "#13708D", backgroundColor: "#13708D" },
  locationTextWrap: { flex: 1, paddingBottom: 10 },
  locationText: { fontSize: 14, fontWeight: "700", color: "#334155" },
  emphasisLocationText: { fontSize: 15, fontWeight: "800", color: "#0F172A" },
  locationTime: { marginTop: 3, fontSize: 11, color: "#64748B" },
  segmentRow: { minHeight: 58, flexDirection: "row" },
  segmentLine: {
    position: "absolute",
    top: -30,
    bottom: -14,
    width: 4,
    borderRadius: 2,
  },
  segmentIcon: {
    width: 26,
    height: 26,
    marginTop: 4,
    borderRadius: 13,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 2,
  },
  liveBusMarker: {
    position: "absolute",
    width: 24,
    height: 24,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderRadius: 12,
    backgroundColor: "#FFFFFF",
    zIndex: 3,
  },
  segmentContent: {
    flex: 1,
    marginLeft: 2,
    marginBottom: 12,
    padding: 11,
    borderRadius: 13,
    backgroundColor: "#F8FAFC",
  },
  segmentTitle: { fontSize: 13, fontWeight: "700", color: "#334155" },
  segmentMeta: { marginTop: 4, fontSize: 11, color: "#64748B" },
  liveBusText: { marginTop: 5, fontSize: 11, fontWeight: "700", color: "#13708D" },
});

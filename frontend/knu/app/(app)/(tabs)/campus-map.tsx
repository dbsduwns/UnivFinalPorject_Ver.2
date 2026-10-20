import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  AppState,
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
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  Footprints,
  MapPinned,
  Navigation,
  TrainFront,
} from "lucide-react-native";

import { AppScreenLayout } from "@/components/ui/AppScreenLayout";
import {
  getTransitLive,
  transitLiveRequest,
  commuteTodayOptions,
} from "@/features/commute/api/commute";
import { useAuthStore } from "@/features/auth/store/auth-store";
import type {
  LiveBusPosition,
  RouteCoordinate,
  RouteStop,
  RouteStep,
  TransitLive,
} from "@/features/commute/api/types";

const GOOGLE_MAP_ID = process.env.EXPO_PUBLIC_GOOGLE_MAP_ID?.trim();
const { height: SCREEN_HEIGHT } = Dimensions.get("window");
const SHEET_MAX_HEIGHT = Math.min(SCREEN_HEIGHT * 0.7, 620);
const SHEET_MIN_HEIGHT = 112;
const SHEET_COLLAPSED_Y = SHEET_MAX_HEIGHT - SHEET_MIN_HEIGHT;
const SHEET_HALF_Y = SHEET_COLLAPSED_Y * 0.48;
const TRANSIT_FALLBACK_COLORS = ["#13708D", "#7C3AED", "#DC2626", "#D97706"];
const VEHICLE_MARKER_ANIMATION_MS = 700;
const VEHICLE_MARKER_ANIMATION_STEPS = 10;

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

function getVehicleRouteStopOrder(vehicle: LiveBusPosition, routeStops: RouteStop[]) {
  const normalizeStopName = (value: string | null | undefined) =>
    (value ?? "").replace(/[\s.·ㆍ()（）]/g, "").toLowerCase();
  const matchedStop = vehicle.current_stop_id
    ? routeStops.find((stop) => stop.stop_id === vehicle.current_stop_id)
    : undefined;
  const matchedByName = !matchedStop && vehicle.current_stop_name
    ? routeStops.find((stop) => normalizeStopName(stop.stop_name) === normalizeStopName(vehicle.current_stop_name))
    : undefined;
  return matchedStop?.stop_order ?? matchedByName?.stop_order ?? vehicle.current_stop_order;
}

function TransitStopAccordion({
  step,
  stepIndex,
  color,
  pollingEnabled,
  expanded,
  onToggle,
  onLiveDataChange,
}: {
  step: RouteStep;
  stepIndex: number;
  color: string;
  pollingEnabled: boolean;
  expanded: boolean;
  onToggle: () => void;
  onLiveDataChange: (stepIndex: number, data: TransitLive | null) => void;
}) {
  const request = useMemo(() => transitLiveRequest(step), [step]);
  const canLoadRealtime = Boolean(
    (step.vehicle_type?.includes("BUS") || step.vehicle_type?.includes("SUBWAY")) && step.transit_line_name &&
    step.departure_stop_name && step.arrival_stop_name,
  );
  const realtimeQueryEnabled = pollingEnabled && expanded && canLoadRealtime;
  const { data, isFetching, isError: isLiveError } = useQuery({
    queryKey: ["commute", "transit-live", request],
    queryFn: ({ signal }) => getTransitLive(request, signal),
    enabled: realtimeQueryEnabled,
    staleTime: (query) => (query.state.data?.refresh_after_seconds ?? 30) * 1000,
    gcTime: 10 * 60_000,
    refetchInterval: (query) => {
      if (!realtimeQueryEnabled) return false;
      if (["unsupported", "unmatched", "not_configured"].includes(query.state.data?.status ?? "")) return false;
      if (query.state.error) return 60_000;
      return (query.state.data?.refresh_after_seconds ?? 30) * 1000;
    },
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: false,
  });
  useEffect(() => {
    onLiveDataChange(stepIndex, realtimeQueryEnabled ? data ?? null : null);
    return () => onLiveDataChange(stepIndex, null);
  }, [data, onLiveDataChange, realtimeQueryEnabled, stepIndex]);
  // 응답에는 탑승 전 5개부터 하차 후 3개까지의 연속 정류장 구간이 포함된다.
  const visibleStops = data?.route_stops ?? [];
  const boardingOrder = data?.boarding_stop_order;
  const alightingOrder = data?.alighting_stop_order;
  const liveBuses = useMemo(
    () => (isLiveError ? [] : data?.vehicles ?? [])
      .slice()
      .sort((first, second) =>
        (getVehicleRouteStopOrder(first, data?.route_stops ?? []) ?? Number.MAX_SAFE_INTEGER) -
        (getVehicleRouteStopOrder(second, data?.route_stops ?? []) ?? Number.MAX_SAFE_INTEGER)),
    [data?.route_stops, data?.vehicles, isLiveError],
  );
  const arrivalMinutes = isLiveError ? null : data?.arrival_minutes ?? null;
  const isSubway = step.vehicle_type?.includes("SUBWAY") ?? false;
  const scheduledDeparture = step.scheduled_departure_time
    ? new Date(step.scheduled_departure_time).toLocaleTimeString("ko-KR", {
        hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Seoul",
      })
    : null;
  const arrivalLabel = isLiveError ? "실시간 조회 실패"
    : !expanded ? (scheduledDeparture ? `${scheduledDeparture} 예정` : "펼쳐서 확인")
    : arrivalMinutes !== null ? (arrivalMinutes === 0 ? "곧 도착" : `${arrivalMinutes}분 후`)
    : isFetching && !data ? "확인 중"
    : data?.status === "provider_error" ? "실시간 조회 실패"
    : data?.status === "no_data" ? "도착 예정 미제공"
    : scheduledDeparture ? `${scheduledDeparture} 예정` : "실시간 정보 미지원";
  return (
    <View style={styles.transitStopCard}>
      <View style={styles.transitStopHeader}>
        <View style={styles.transitStopTitleWrap}>
          <Text style={styles.transitStopTitle}>
            {step.departure_stop_name ?? "탑승 정류장"}
          </Text>
          <Text style={[styles.transitLineName, { color }]}>
            {step.transit_line_name ?? "대중교통"}
          </Text>
        </View>
        <View style={[styles.nextVehicleBadge, { backgroundColor: `${color}18` }]}>
          <Text style={[styles.nextVehicleText, { color }]}>
            {arrivalLabel}
          </Text>
        </View>
      </View>

      <TouchableOpacity
        style={styles.stopExpandButton}
        activeOpacity={0.7}
        onPress={onToggle}
      >
        <Text style={styles.stopExpandText}>
          {visibleStops.length > 0
            ? step.stop_count
              ? `${step.stop_count}개 정류장 · 구간 보기`
              : "탑승·하차 구간 정류장"
            : expanded && isFetching
              ? "정류장 확인 중"
              : step.stop_count
                ? `${step.stop_count}개 정류장 · 펼쳐서 확인`
                : canLoadRealtime
                ? "경유 정류장 보기"
                : "정류장 정보 없음"}
        </Text>
        <ChevronDown
          size={18}
          color="#475569"
          style={{ transform: [{ rotate: expanded ? "180deg" : "0deg" }] }}
        />
      </TouchableOpacity>

      {expanded && (
        <View style={styles.stopList}>
          {data && (
            <Text style={styles.stopEmptyText}>
              {`${new Date(data.cached_at).toLocaleTimeString("ko-KR", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                timeZone: "Asia/Seoul",
              })} 조회 기준`}
            </Text>
          )}
          {data?.message && (
            <Text style={[styles.vehiclePositionNotice, styles.vehiclePositionWarning]}>
              {data.message}
            </Text>
          )}
          {data?.vehicle_position_message && (
            <Text style={[
              styles.vehiclePositionNotice,
              data.vehicle_position_status === "unavailable" && styles.vehiclePositionWarning,
            ]}>
              {data.vehicle_position_message}
            </Text>
          )}
          <ScrollView
            style={styles.stopListScroll}
            contentContainerStyle={styles.stopListScrollContent}
            nestedScrollEnabled
            showsVerticalScrollIndicator
          >
            {visibleStops.map((stop) => {
              const isBoarding = stop.stop_order === boardingOrder;
              const isArrival = stop.stop_order === alightingOrder;
              const vehiclesAtStop = liveBuses.filter((vehicle) =>
                getVehicleRouteStopOrder(vehicle, data?.route_stops ?? []) === stop.stop_order,
              );
              const isBeforeBoarding =
                boardingOrder !== undefined && stop.stop_order < boardingOrder;
              return (
                <View key={`${stop.stop_id}-${stop.stop_order}`}>
                  <View style={styles.stopRow}>
                    <View style={styles.stopRail}>
                      <View style={[
                        styles.stopDot,
                        { borderColor: color },
                        (isBoarding || isArrival) && { backgroundColor: color },
                      ]} />
                      {!isArrival && <View style={[styles.stopLine, { backgroundColor: color }]} />}
                    </View>
                    <View style={styles.stopNameWrap}>
                      <Text style={[
                        styles.stopName,
                        (isBoarding || isArrival) && styles.stopNameEmphasis,
                        isBeforeBoarding && styles.stopNameApproaching,
                      ]}>
                        {stop.stop_name}
                      </Text>
                      {isBoarding && <Text style={styles.stopCaption}>탑승</Text>}
                      {isArrival && <Text style={styles.stopCaption}>하차</Text>}
                    </View>
                    {vehiclesAtStop.length > 0 && (
                      <View style={styles.vehiclePositionBadges}>
                        {vehiclesAtStop.map((vehicle) => (
                          <View
                            key={`${stop.stop_id}-${vehicle.vehicle_number}`}
                            style={[styles.vehiclePositionBadge, { borderColor: color }]}
                          >
                            {isSubway ? <TrainFront size={12} color={color} /> : <Bus size={12} color={color} />}
                            <Text style={[styles.vehiclePositionText, { color }]}>
                              {isSubway
                                ? [
                                  vehicle.vehicle_number,
                                  vehicle.destination_name ? `${vehicle.destination_name} 방면` : null,
                                  vehicle.direction,
                                ].filter(Boolean).join(" · ")
                                : `${vehicle.vehicle_number} · ${vehicle.position_source === "gps"
                                  ? "GPS"
                                  : vehicle.position_source === "map_matched"
                                    ? "도로"
                                    : "정류장"}`}
                            </Text>
                          </View>
                        ))}
                      </View>
                    )}
                  </View>
                </View>
              );
            })}
            {visibleStops.length === 0 && (
              <Text style={styles.stopEmptyText}>
                {isFetching && !data ? "경유 정류장을 확인하고 있어요"
                  : isLiveError ? "잠시 후 다시 확인해주세요."
                  : data?.message ?? "이 구간은 예정 시간으로 안내합니다."}
              </Text>
            )}
          </ScrollView>
        </View>
      )}
    </View>
  );
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
      longitude: (minLongitude + maxLongitude) /2,
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
  const userId = useAuthStore((state) => state.user?.id);
  const [isAppActive, setIsAppActive] = useState(AppState.currentState === "active");
  const [expandedStepIndex, setExpandedStepIndex] = useState<number | null>(null);
  const [isSheetExpanded, setIsSheetExpanded] = useState(true);
  const [activeTransitLive, setActiveTransitLive] = useState<{
    stepIndex: number;
    data: TransitLive;
  } | null>(null);
  const [displayedLiveVehicles, setDisplayedLiveVehicles] = useState<LiveBusPosition[]>([]);
  const displayedLiveVehiclesRef = useRef<LiveBusPosition[]>([]);
  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => setIsAppActive(state === "active"));
    return () => subscription.remove();
  }, []);
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
  const busMarkerIcon = useImage(
    require("../../../src/assets/images/map-marker-bus.png"),
    { maxWidth: 72, maxHeight: 72 },
  );
  const [mapMode, setMapMode] = useState<MapMode>(
    mode === "commute" ? "commute" : "campus",
  );
  const [isMapLoaded, setIsMapLoaded] = useState(false);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [isDetailView, setIsDetailView] = useState(false);
  const [routeFocusRequest, setRouteFocusRequest] = useState(0);
  const mapRef = useRef<GoogleMaps.MapView>(null);
  const sheetTranslateY = useRef(new Animated.Value(SHEET_HALF_Y)).current;
  const sheetPositionRef = useRef(SHEET_HALF_Y);
  const dragStartRef = useRef(SHEET_HALF_Y);

  const handleLiveDataChange = useCallback((
    stepIndex: number,
    data: TransitLive | null,
  ) => {
    setActiveTransitLive((current) => {
      if (data) return { stepIndex, data };
      return current?.stepIndex === stepIndex ? null : current;
    });
  }, []);

  // 새 위치가 도착하면 마커를 짧게 보간해 API 갱신 사이의 급격한 점프를 줄인다.
  useEffect(() => {
    const targets = activeTransitLive?.data.vehicles.filter(
      (vehicle) => vehicle.latitude !== null && vehicle.longitude !== null,
    ) ?? [];
    if (targets.length === 0) {
      displayedLiveVehiclesRef.current = [];
      setDisplayedLiveVehicles([]);
      return;
    }

    const previousByNumber = new Map(
      displayedLiveVehiclesRef.current.map((vehicle) => [vehicle.vehicle_number, vehicle]),
    );
    const canAnimate = targets.some((vehicle) => {
      const previous = previousByNumber.get(vehicle.vehicle_number);
      return previous?.latitude !== null && previous?.longitude !== null;
    });
    if (!canAnimate) {
      displayedLiveVehiclesRef.current = targets;
      setDisplayedLiveVehicles(targets);
      return;
    }

    let step = 0;
    const timer = setInterval(() => {
      step += 1;
      const progress = step / VEHICLE_MARKER_ANIMATION_STEPS;
      const eased = 1 - (1 - progress) ** 3;
      const next = targets.map((target) => {
        const previous = previousByNumber.get(target.vehicle_number);
        if (
          !previous || previous.latitude === null || previous.longitude === null ||
          target.latitude === null || target.longitude === null
        ) return target;
        return {
          ...target,
          latitude: previous.latitude + (target.latitude - previous.latitude) * eased,
          longitude: previous.longitude + (target.longitude - previous.longitude) * eased,
        };
      });
      displayedLiveVehiclesRef.current = next;
      setDisplayedLiveVehicles(next);
      if (step >= VEHICLE_MARKER_ANIMATION_STEPS) clearInterval(timer);
    }, VEHICLE_MARKER_ANIMATION_MS / VEHICLE_MARKER_ANIMATION_STEPS);
    return () => clearInterval(timer);
  }, [activeTransitLive]);

  const snapSheet = useCallback((position: number) => {
    const clampedPosition = Math.max(0, Math.min(SHEET_COLLAPSED_Y, position));
    setIsSheetExpanded(clampedPosition < SHEET_COLLAPSED_Y);
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
    ...commuteTodayOptions(userId, "depart_now"),
    enabled: mapMode === "commute" && isFocused && isAppActive && userId !== undefined,
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
    setExpandedStepIndex(null);
    setActiveTransitLive(null);
    setIsDetailView(false);
    snapSheet(SHEET_HALF_Y);
  }, [commute?.calculated_at, snapSheet]);

  const openRouteDetail = (index: number) => {
    setSelectedRouteIndex(index);
    setExpandedStepIndex(null);
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

  const liveVehicleMarkers = useMemo(
    () => activeTransitLive ? displayedLiveVehicles
      .map((vehicle, index) => ({
        id: `live-bus-${activeTransitLive.stepIndex}-${vehicle.vehicle_number}-${index}`,
        coordinates: {
          latitude: vehicle.latitude as number,
          longitude: vehicle.longitude as number,
        },
        title: `🚌 ${vehicle.vehicle_number}`,
        snippet: vehicle.position_source === "gps"
          ? "GPS 기반 실시간 위치"
          : vehicle.position_source === "map_matched"
            ? "도로에 보정된 실시간 위치"
            : `정류장 기준 위치${vehicle.current_stop_name ? ` · ${vehicle.current_stop_name}` : ""}`,
        zIndex: 20,
        icon: busMarkerIcon ?? undefined,
        anchor: { x: 0.5, y: 0.5 },
        showCallout: true,
      })) : [],
    [activeTransitLive, busMarkerIcon, displayedLiveVehicles],
  );

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
          ...liveVehicleMarkers,
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

                {route.recommendation_reason && (
                  <View style={styles.realtimeReasonCard}>
                    <Bus size={15} color="#13708D" />
                    <Text style={styles.realtimeReasonText}>
                      {route.recommendation_reason}
                    </Text>
                  </View>
                )}

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
                    return (
                      <View key={`segment-${item.stepIndex}-${index}`} style={styles.segmentRow}>
                        <View style={styles.timelineLeftColumn}>
                          <View style={[styles.segmentLine, { backgroundColor: color }]} />
                          <View style={[styles.segmentIcon, { backgroundColor: color }]}>
                            <RouteStepIcon step={item.step} color="#FFFFFF" size={14} />
                          </View>
                        </View>
                        <View style={styles.segmentContent}>
                          <Text style={styles.segmentTitle}>{getStepLabel(item.step)}</Text>
                          <Text style={styles.segmentMeta}>
                            {item.step.duration_minutes}분
                            {item.step.distance_meters > 0
                              ? ` · ${item.step.distance_meters}m`
                              : ""}
                          </Text>
                          {item.step.travel_mode === "TRANSIT" && (
                            <TransitStopAccordion
                              step={item.step}
                              stepIndex={item.stepIndex}
                              color={color}
                              pollingEnabled={isFocused && isAppActive && isDetailView && isSheetExpanded && mapMode === "commute"}
                              expanded={expandedStepIndex === item.stepIndex}
                              onToggle={() => setExpandedStepIndex((current) => current === item.stepIndex ? null : item.stepIndex)}
                              onLiveDataChange={handleLiveDataChange}
                            />
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
  realtimeReasonCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    marginTop: 9,
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderRadius: 12,
    backgroundColor: "#EAF8FC",
  },
  realtimeReasonText: { flex: 1, fontSize: 11, fontWeight: "700", color: "#0F5D73" },
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
  transitStopCard: {
    marginTop: 10,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#E2E8F0",
    borderRadius: 14,
    backgroundColor: "#FFFFFF",
  },
  transitStopHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
    paddingHorizontal: 13,
    paddingVertical: 12,
  },
  transitStopTitleWrap: { flex: 1 },
  transitStopTitle: { fontSize: 14, fontWeight: "800", color: "#0F172A" },
  transitLineName: { marginTop: 3, fontSize: 12, fontWeight: "700" },
  nextVehicleBadge: { paddingHorizontal: 10, paddingVertical: 7, borderRadius: 10 },
  nextVehicleText: { fontSize: 12, fontWeight: "800" },
  stopExpandButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 5,
    minHeight: 42,
    borderTopWidth: 1,
    borderTopColor: "#E2E8F0",
  },
  stopExpandText: { fontSize: 12, fontWeight: "800", color: "#334155" },
  stopList: {
    paddingHorizontal: 13,
    paddingTop: 6,
    paddingBottom: 10,
    borderTopWidth: 1,
    borderTopColor: "#E2E8F0",
    backgroundColor: "#FCFDFE",
  },
  stopListScroll: { maxHeight: 260 },
  stopListScrollContent: { paddingBottom: 4 },
  stopRow: { minHeight: 42, flexDirection: "row", alignItems: "stretch" },
  stopRail: { width: 24, alignItems: "center" },
  stopDot: {
    width: 10,
    height: 10,
    marginTop: 15,
    borderWidth: 2,
    borderRadius: 5,
    backgroundColor: "#FFFFFF",
    zIndex: 2,
  },
  stopLine: { position: "absolute", top: 24, bottom: -15, width: 2 },
  stopNameWrap: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    paddingLeft: 5,
  },
  stopName: { flexShrink: 1, fontSize: 12, color: "#475569" },
  stopNameEmphasis: { fontWeight: "800", color: "#0F172A" },
  stopNameApproaching: { color: "#94A3B8" },
  stopCaption: { fontSize: 10, fontWeight: "800", color: "#13708D" },
  vehiclePositionBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 7,
    paddingVertical: 5,
    borderWidth: 1,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
  },
  vehiclePositionBadges: {
    maxWidth: "55%",
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "flex-end",
    alignContent: "center",
    gap: 4,
    paddingVertical: 4,
  },
  vehiclePositionText: { fontSize: 10, fontWeight: "800" },
  vehiclePositionNotice: {
    marginHorizontal: 6,
    marginBottom: 8,
    paddingHorizontal: 9,
    paddingVertical: 7,
    borderRadius: 9,
    backgroundColor: "#EAF8FC",
    textAlign: "center",
    fontSize: 10,
    fontWeight: "700",
    color: "#0F5D73",
  },
  vehiclePositionWarning: { backgroundColor: "#FFF1F2", color: "#BE123C" },
  stopEmptyText: {
    paddingVertical: 14,
    textAlign: "center",
    fontSize: 11,
    color: "#64748B",
  },
});

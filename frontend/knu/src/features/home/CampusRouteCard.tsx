import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { ChevronRight, Clock3, Home, MapPin, Navigation } from "lucide-react-native";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { getTodayCommute } from "@/features/commute/api/commute";
import type { CommuteToday, RouteSummary } from "@/features/commute/api/types";

const formatTime = (value: string | null | undefined) => value?.slice(0, 5) ?? null;

function getCardCopy(commute: CommuteToday | undefined) {
  if (!commute) {
    return {
      title: "집에서 강남대학교까지",
      description: "맞춤 등교 정보를 불러오고 있어요",
      action: "불러오는 중",
    };
  }

  const route = commute.recommended_route;
  if (commute.status === "ready" && route) {
    const departureTime = formatTime(route.departure_time);
    const destination = commute.destination?.destination_name;

    if (!commute.first_class) {
      const travelTime = `학교까지 약 ${route.duration_minutes}분`;
      return {
        title: commute.message ?? "오늘 예정된 정규 수업이 없습니다.",
        description: [travelTime, destination].filter(Boolean).join(" · "),
        action: "경로보기",
      };
    }

    const title =
      commute.display_mode === "departure_recommendation" && departureTime
        ? `${departureTime}에 출발하세요`
        : `학교까지 약 ${route.duration_minutes}분`;
    const classTime = formatTime(commute.first_class?.start_time);
    const classLabel = commute.first_class?.course_name;
    const description = [
      classTime && classLabel ? `${classTime} ${classLabel}` : classLabel,
      destination,
    ]
      .filter(Boolean)
      .join(" · ");

    return {
      title,
      description: description || route.recommendation_reason || "추천 경로를 확인해보세요",
      action: "경로보기",
    };
  }

  if (commute.status === "setup_required") {
    return {
      title: "집 주소를 등록해주세요",
      description: commute.message ?? "주소를 등록하면 맞춤 등교 시간을 알려드려요",
      action: "설정하기",
    };
  }

  if (commute.status === "no_schedule") {
    return {
      title: "오늘은 정규 수업이 없어요",
      description: commute.message ?? "여유로운 하루를 보내세요",
      action: "캠퍼스맵",
    };
  }

  return {
    title: "등교 경로를 계산하지 못했어요",
    description: commute.message ?? "캠퍼스맵에서 경로를 다시 확인해주세요",
    action: commute.status === "provider_error" ? "다시 확인" : "캠퍼스맵",
  };
}

function getSecondaryInfo(route: RouteSummary | null | undefined) {
  if (!route) return "대중교통 추천";
  if (route.bus_arrival_minutes !== null) {
    return `버스 ${route.bus_arrival_minutes}분 후`;
  }
  const shuttleTime = formatTime(route.shuttle_departure_time);
  if (shuttleTime) return `셔틀 ${shuttleTime}`;
  return route.transfer_count > 0 ? `환승 ${route.transfer_count}회` : "환승 없음";
}

export const CampusRouteCard = () => {
  const [isSetupModalVisible, setIsSetupModalVisible] = useState(false);
  const [hasRequestedCommute, setHasRequestedCommute] = useState(false);
  const commuteQuery = useQuery({
    queryKey: ["commute", "today"],
    queryFn: getTodayCommute,
    enabled: false,
    retry: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
  });

  const copy = hasRequestedCommute
    ? getCardCopy(commuteQuery.data)
    : {
        title: "오늘의 등교 시간을 확인해보세요",
        description: "버튼을 누르면 첫 수업에 맞춰 추천 출발 시간을 계산해드려요",
        action: "등교 시간 계산하기",
      };
  const route = hasRequestedCommute ? commuteQuery.data?.recommended_route : undefined;
  const hasRequestError = hasRequestedCommute && commuteQuery.isError;
  const shouldRetry =
    hasRequestedCommute &&
    (hasRequestError || commuteQuery.data?.status === "provider_error");
  const isCalculating = hasRequestedCommute && commuteQuery.isFetching;

  const calculateCommute = () => {
    if (commuteQuery.isFetching) return;
    setHasRequestedCommute(true);
    void commuteQuery.refetch();
  };

  const handlePress = () => {
    if (shouldRetry) {
      calculateCommute();
      return;
    }
    if (commuteQuery.data?.status === "setup_required") {
      setIsSetupModalVisible(true);
      return;
    }
    router.push({
      pathname: "/(app)/(tabs)/campus-map",
      params: { mode: "commute" },
    });
  };

  const handleActionPress = () => {
    if (!hasRequestedCommute || shouldRetry) {
      calculateCommute();
      return;
    }
    handlePress();
  };

  const openCommuteSettings = () => {
    setIsSetupModalVisible(false);
    router.push("/(app)/commute-settings");
  };

  return (
    <View style={styles.section}>
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.headerTitleWrap}>
            <Navigation size={22} color="#13708D" />
            <Text style={styles.sectionTitle}>오늘의 등교 길찾기</Text>
          </View>
          <TouchableOpacity
            style={styles.headerLink}
            activeOpacity={0.6}
            onPress={() => router.push({
              pathname: "/(app)/(tabs)/campus-map",
              params: {
                mode: "commute",
              },
            })}
          >
            <Text style={styles.moreText}>캠퍼스맵</Text>
            <ChevronRight size={16} color="#13708D" />
          </TouchableOpacity>
        </View>

        <View style={styles.cardTopRow}>
          <View style={styles.routeLine}>
            <View style={styles.routeIcon}>
              <Home size={17} color="#13708D" />
            </View>
            <View style={styles.routeConnector} />
            <View style={[styles.routeIcon, styles.schoolIcon]}>
              <MapPin size={17} color="#FFFFFF" />
            </View>
          </View>
          <View style={styles.routeTitleWrap}>
            {isCalculating ? (
              <View style={styles.loadingRow}>
                <ActivityIndicator size="small" color="#13708D" />
                <Text style={styles.loadingText}>등교 시간을 계산하고 있어요</Text>
              </View>
            ) : (
              <>
                <Text style={styles.routeTitle}>
                  {hasRequestError ? "등교 정보를 불러오지 못했어요" : copy.title}
                </Text>
                <Text style={styles.routeDescription} numberOfLines={2}>
                  {hasRequestError
                    ? "네트워크 상태를 확인한 뒤 다시 시도해주세요"
                    : copy.description}
                </Text>
              </>
            )}
          </View>
          <ChevronRight size={20} color="#13708D" />
        </View>

        <View style={styles.divider} />
        <View style={styles.cardBottomRow}>
          <View style={styles.infoItem}>
            <Clock3 size={16} color="#13708D" />
            <Text style={styles.infoText}>
              {route ? `총 ${route.duration_minutes}분` : "출발 시간 계산"}
            </Text>
          </View>
          <View style={styles.infoItem}>
            <Navigation size={16} color="#13708D" />
            <Text style={styles.infoText}>{getSecondaryInfo(route)}</Text>
          </View>
          <TouchableOpacity
            style={styles.actionButton}
            activeOpacity={0.6}
            disabled={isCalculating}
            onPress={handleActionPress}
          >
            <Text style={styles.actionText}>
              {isCalculating
                ? "계산 중"
                : !hasRequestedCommute
                  ? "계산하기"
                  : shouldRetry
                    ? "다시 계산"
                    : copy.action}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <Modal
        visible={isSetupModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setIsSetupModalVisible(false)}
      >
        <View style={styles.modalBackdrop}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={() => setIsSetupModalVisible(false)}
          />
          <View style={styles.modalCard}>
            <View style={styles.modalIcon}>
              <Navigation size={26} color="#13708D" />
            </View>
            <Text style={styles.modalTitle}>맞춤 등교 시간을 확인해보세요</Text>
            <Text style={styles.modalDescription}>
              집 주소를 등록하면 첫 수업과 셔틀 시간에 맞춰 추천 출발 시간을 계산해드려요.
            </Text>
            <View style={styles.modalButtons}>
              <Pressable
                style={styles.laterButton}
                onPress={() => setIsSetupModalVisible(false)}
              >
                <Text style={styles.laterButtonText}>나중에</Text>
              </Pressable>
              <Pressable style={styles.setupButton} onPress={openCommuteSettings}>
                <Text style={styles.setupButtonText}>집 주소 등록</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  section: { marginBottom: 24, backgroundColor: "white", borderRadius: 15 },
  cardHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginHorizontal: 24, marginTop: 20, marginBottom: 18 },
  headerTitleWrap: { flexDirection: "row", alignItems: "center", gap: 8 },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#111827" },
  headerLink: { flexDirection: "row", alignItems: "center" },
  moreText: { color: "#13708D", fontSize: 12, fontWeight: "600", marginRight: 2 },
  card: { backgroundColor: "white", borderWidth: 1, borderRadius: 15, borderColor: "#E5E7EB", width: "100%" },
  cardPressed: { opacity: 0.82 },
  cardTopRow: { flexDirection: "row", alignItems: "center", marginHorizontal: 24, marginBottom: 18 },
  routeLine: { width: 30, alignItems: "center", marginRight: 12 },
  routeIcon: { width: 30, height: 30, borderRadius: 15, backgroundColor: "#EAF8FC", alignItems: "center", justifyContent: "center" },
  schoolIcon: { backgroundColor: "#13708D" },
  routeConnector: { width: 2, height: 10, backgroundColor: "#B5DDE5" },
  routeTitleWrap: { flex: 1 },
  routeTitle: { fontSize: 16, fontWeight: "700", color: "#0F172A", marginBottom: 5 },
  routeDescription: { fontSize: 12, color: "#64748B", lineHeight: 17 },
  loadingRow: { flexDirection: "row", alignItems: "center" },
  loadingText: { marginLeft: 8, fontSize: 13, color: "#64748B" },
  divider: { height: 1, backgroundColor: "#F3F4F6", marginHorizontal: 24, marginBottom: 16 },
  cardBottomRow: { flexDirection: "row", alignItems: "center", marginHorizontal: 24, marginBottom: 20 },
  infoItem: { flexDirection: "row", alignItems: "center", marginRight: 14 },
  infoText: { marginLeft: 5, fontSize: 11, color: "#475569" },
  actionButton: { marginLeft: "auto", paddingVertical: 4, paddingLeft: 8 },
  actionText: { fontSize: 12, fontWeight: "700", color: "#13708D" },
  modalBackdrop: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, backgroundColor: "rgba(15, 23, 42, 0.45)" },
  modalCard: { width: "100%", maxWidth: 360, padding: 24, borderRadius: 22, alignItems: "center", backgroundColor: "#FFFFFF" },
  modalIcon: { width: 52, height: 52, borderRadius: 26, alignItems: "center", justifyContent: "center", backgroundColor: "#EAF8FC", marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: "700", color: "#0F172A", textAlign: "center" },
  modalDescription: { marginTop: 9, fontSize: 13, lineHeight: 20, color: "#64748B", textAlign: "center" },
  modalButtons: { width: "100%", flexDirection: "row", gap: 10, marginTop: 22 },
  laterButton: { flex: 1, height: 46, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: "#F1F5F9" },
  laterButtonText: { fontSize: 14, fontWeight: "600", color: "#64748B" },
  setupButton: { flex: 1.4, height: 46, borderRadius: 12, alignItems: "center", justifyContent: "center", backgroundColor: "#13708D" },
  setupButtonText: { fontSize: 14, fontWeight: "700", color: "#FFFFFF" },
});

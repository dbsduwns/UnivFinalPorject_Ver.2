import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { router } from "expo-router";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import {
  ArrowLeft,
  BusFront,
  Check,
  ChevronRight,
  Clock3,
  Home,
  MapPin,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { getAxiosErrorMessage } from "@/api/errors";
import {
  createCommuteProfile,
  deleteCommuteProfile,
  getCommuteProfileOrNull,
  searchCommuteAddresses,
  updateCommuteProfile,
} from "@/features/commute/api/commute";
import type {
  CommuteAddressSearchResult,
  CommuteProfileCreate,
  CommuteProfileUpdate,
} from "@/features/commute/api/types";

const BUFFER_OPTIONS = [5, 10, 15, 20];

export default function CommuteSettingsScreen() {
  const queryClient = useQueryClient();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CommuteAddressSearchResult[]>([]);
  const [selectedAddress, setSelectedAddress] = useState<CommuteAddressSearchResult | null>(null);
  const [useShuttle, setUseShuttle] = useState(false);
  const [bufferMinutes, setBufferMinutes] = useState(10);

  const profileQuery = useQuery({
    queryKey: ["commute", "profile"],
    queryFn: getCommuteProfileOrNull,
  });

  useEffect(() => {
    if (!profileQuery.data) return;
    setUseShuttle(profileQuery.data.use_shuttle);
    setBufferMinutes(profileQuery.data.departure_buffer_minutes);
  }, [profileQuery.data]);

  const searchMutation = useMutation({
    mutationFn: searchCommuteAddresses,
    onSuccess: (data) => {
      setResults(data);
      if (data.length === 0) {
        Alert.alert("검색 결과 없음", "도로명, 건물명 또는 지번을 다시 확인해주세요.");
      }
    },
    onError: (error) => {
      Alert.alert("주소 검색 실패", getAxiosErrorMessage(error));
    },
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const profile = profileQuery.data;
      if (!profile && !selectedAddress) {
        throw new Error("집 주소를 먼저 검색하고 선택해주세요.");
      }

      if (profile) {
        const body: CommuteProfileUpdate = {
          use_shuttle: useShuttle,
          departure_buffer_minutes: bufferMinutes,
        };
        if (selectedAddress) {
          body.home_address = selectedAddress.address;
          body.home_road_address = selectedAddress.road_address;
          body.home_latitude = selectedAddress.latitude;
          body.home_longitude = selectedAddress.longitude;
        }
        return updateCommuteProfile(body);
      }

      const body: CommuteProfileCreate = {
        home_address: selectedAddress!.address,
        home_road_address: selectedAddress!.road_address,
        home_latitude: selectedAddress!.latitude,
        home_longitude: selectedAddress!.longitude,
        use_shuttle: useShuttle,
        departure_buffer_minutes: bufferMinutes,
      };
      return createCommuteProfile(body);
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(["commute", "profile"], profile);
      void queryClient.invalidateQueries({ queryKey: ["commute", "today"] });
      Alert.alert("저장 완료", "등교 설정이 저장되었습니다.", [
        { text: "확인", onPress: () => router.back() },
      ]);
    },
    onError: (error) => {
      const message = error instanceof Error && !('response' in error)
        ? error.message
        : getAxiosErrorMessage(error, "등교 설정 저장에 실패했습니다.");
      Alert.alert("저장 실패", message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCommuteProfile,
    onSuccess: () => {
      queryClient.setQueryData(["commute", "profile"], null);
      void queryClient.invalidateQueries({ queryKey: ["commute", "today"] });
      Alert.alert("삭제 완료", "등록된 집 주소와 등교 설정을 삭제했습니다.", [
        { text: "확인", onPress: () => router.back() },
      ]);
    },
    onError: (error) => {
      Alert.alert("삭제 실패", getAxiosErrorMessage(error));
    },
  });

  const handleSearch = () => {
    const normalized = query.trim();
    if (normalized.length < 2) {
      Alert.alert("주소 입력", "두 글자 이상 입력해주세요.");
      return;
    }
    searchMutation.mutate(normalized);
  };

  const handleDelete = () => {
    Alert.alert(
      "등교 설정 삭제",
      "집 주소와 셔틀 설정을 모두 삭제할까요?",
      [
        { text: "취소", style: "cancel" },
        { text: "삭제", style: "destructive", onPress: () => deleteMutation.mutate() },
      ],
    );
  };

  const currentAddress = selectedAddress?.road_address
    || selectedAddress?.address
    || profileQuery.data?.home_road_address
    || profileQuery.data?.home_address;

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.header}>
          <Pressable style={styles.headerButton} onPress={() => router.back()}>
            <ArrowLeft size={22} color="#0F172A" />
          </Pressable>
          <Text style={styles.headerTitle}>등교 설정</Text>
          <View style={styles.headerButton} />
        </View>

        <ScrollView
          style={styles.flex}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.introCard}>
            <View style={styles.introIcon}>
              <Home size={22} color="#13708D" />
            </View>
            <View style={styles.flex}>
              <Text style={styles.introTitle}>내 등교 경로를 설정해보세요</Text>
              <Text style={styles.introText}>
                첫 수업과 셔틀 시간표를 기준으로 늦지 않는 출발 시간을 계산합니다.
              </Text>
            </View>
          </View>

          <Text style={styles.sectionTitle}>집 주소</Text>
          <View style={styles.sectionCard}>
            {currentAddress ? (
              <View style={styles.currentAddress}>
                <View style={styles.addressPin}>
                  <MapPin size={18} color="#13708D" />
                </View>
                <View style={styles.flex}>
                  <Text style={styles.addressLabel}>
                    {selectedAddress ? "선택한 주소" : "현재 등록된 주소"}
                  </Text>
                  <Text style={styles.addressText}>{currentAddress}</Text>
                </View>
              </View>
            ) : (
              <Text style={styles.emptyAddress}>등록된 집 주소가 없습니다.</Text>
            )}

            <View style={styles.searchRow}>
              <Search size={19} color="#64748B" />
              <TextInput
                value={query}
                onChangeText={setQuery}
                onSubmitEditing={handleSearch}
                placeholder="도로명, 건물명 또는 지번 검색"
                placeholderTextColor="#94A3B8"
                returnKeyType="search"
                style={styles.searchInput}
              />
              <Pressable
                style={[styles.searchButton, searchMutation.isPending && styles.disabledButton]}
                onPress={handleSearch}
                disabled={searchMutation.isPending}
              >
                <Text style={styles.searchButtonText}>
                  {searchMutation.isPending ? "검색 중" : "검색"}
                </Text>
              </Pressable>
            </View>

            {results.length > 0 && (
              <View style={styles.resultsWrap}>
                {results.map((item, index) => {
                  const selected = selectedAddress?.latitude === item.latitude
                    && selectedAddress?.longitude === item.longitude;
                  return (
                    <Pressable
                      key={`${item.latitude}-${item.longitude}-${index}`}
                      style={[styles.resultItem, selected && styles.selectedResult]}
                      onPress={() => setSelectedAddress(item)}
                    >
                      <View style={styles.resultIcon}>
                        {selected
                          ? <Check size={17} color="#FFFFFF" />
                          : <MapPin size={17} color="#64748B" />}
                      </View>
                      <View style={styles.flex}>
                        <Text style={styles.resultTitle}>
                          {item.building_name || item.road_address || item.address}
                        </Text>
                        {item.building_name && item.road_address && (
                          <Text style={styles.resultAddress}>{item.road_address}</Text>
                        )}
                        <Text style={styles.resultAddress}>{item.address}</Text>
                      </View>
                      <ChevronRight size={17} color="#94A3B8" />
                    </Pressable>
                  );
                })}
              </View>
            )}
          </View>

          <Text style={styles.sectionTitle}>이동 설정</Text>
          <View style={styles.sectionCard}>
            <View style={styles.settingRow}>
              <View style={styles.settingIcon}>
                <BusFront size={20} color="#13708D" />
              </View>
              <View style={styles.flex}>
                <Text style={styles.settingTitle}>교내 셔틀버스 이용</Text>
                <Text style={styles.settingDescription}>
                  기흥역에서 이공관까지 셔틀 시간을 반영합니다.
                </Text>
              </View>
              <Switch
                value={useShuttle}
                onValueChange={setUseShuttle}
                trackColor={{ false: "#CBD5E1", true: "#8DD3E5" }}
                thumbColor={useShuttle ? "#13708D" : "#F8FAFC"}
              />
            </View>

            <View style={styles.separator} />
            <View style={styles.bufferHeader}>
              <View style={styles.settingIcon}>
                <Clock3 size={20} color="#13708D" />
              </View>
              <View style={styles.flex}>
                <Text style={styles.settingTitle}>도착 여유 시간</Text>
                <Text style={styles.settingDescription}>수업 시작 전 확보할 여유 시간입니다.</Text>
              </View>
            </View>
            <View style={styles.chipRow}>
              {BUFFER_OPTIONS.map((minutes) => (
                <Pressable
                  key={minutes}
                  style={[styles.chip, bufferMinutes === minutes && styles.selectedChip]}
                  onPress={() => setBufferMinutes(minutes)}
                >
                  <Text style={[styles.chipText, bufferMinutes === minutes && styles.selectedChipText]}>
                    {minutes}분
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          <View style={styles.privacyRow}>
            <ShieldCheck size={17} color="#64748B" />
            <Text style={styles.privacyText}>
              주소는 등교 시간 계산에만 사용되며 다른 사용자에게 공개되지 않습니다.
            </Text>
          </View>

          <Pressable
            style={[styles.saveButton, saveMutation.isPending && styles.disabledButton]}
            onPress={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || profileQuery.isLoading}
          >
            <Text style={styles.saveButtonText}>
              {saveMutation.isPending ? "저장 중..." : "저장하기"}
            </Text>
          </Pressable>

          {profileQuery.data && (
            <Pressable
              style={styles.deleteButton}
              onPress={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 size={17} color="#EF4444" />
              <Text style={styles.deleteText}>등교 설정 삭제</Text>
            </Pressable>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  safeArea: { flex: 1, backgroundColor: "#F3F4F6" },
  header: { height: 58, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: "#FFFFFF", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  headerButton: { width: 40, height: 40, alignItems: "center", justifyContent: "center" },
  headerTitle: { fontSize: 18, fontWeight: "700", color: "#0F172A" },
  content: { padding: 20, paddingBottom: 48 },
  introCard: { flexDirection: "row", padding: 18, borderRadius: 18, backgroundColor: "#EAF8FC", marginBottom: 24 },
  introIcon: { width: 42, height: 42, borderRadius: 21, backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center", marginRight: 12 },
  introTitle: { fontSize: 16, fontWeight: "700", color: "#0F172A", marginBottom: 5 },
  introText: { fontSize: 12, lineHeight: 18, color: "#475569" },
  sectionTitle: { marginLeft: 4, marginBottom: 9, fontSize: 14, fontWeight: "700", color: "#475569" },
  sectionCard: { padding: 18, borderRadius: 18, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E5E7EB", marginBottom: 24 },
  currentAddress: { flexDirection: "row", alignItems: "center", marginBottom: 16 },
  addressPin: { width: 36, height: 36, borderRadius: 18, backgroundColor: "#EAF8FC", alignItems: "center", justifyContent: "center", marginRight: 11 },
  addressLabel: { fontSize: 11, color: "#64748B", marginBottom: 3 },
  addressText: { fontSize: 14, fontWeight: "600", color: "#0F172A", lineHeight: 20 },
  emptyAddress: { fontSize: 13, color: "#64748B", marginBottom: 14 },
  searchRow: { height: 48, flexDirection: "row", alignItems: "center", paddingLeft: 14, borderWidth: 1, borderColor: "#CBD5E1", borderRadius: 12, backgroundColor: "#F8FAFC" },
  searchInput: { flex: 1, marginLeft: 8, fontSize: 14, color: "#0F172A" },
  searchButton: { height: 38, minWidth: 64, marginRight: 5, borderRadius: 9, alignItems: "center", justifyContent: "center", backgroundColor: "#13708D" },
  searchButtonText: { color: "#FFFFFF", fontSize: 12, fontWeight: "700" },
  resultsWrap: { marginTop: 12, borderTopWidth: 1, borderTopColor: "#F1F5F9" },
  resultItem: { flexDirection: "row", alignItems: "center", paddingVertical: 13, paddingHorizontal: 8, borderBottomWidth: 1, borderBottomColor: "#F1F5F9" },
  selectedResult: { marginHorizontal: -4, paddingHorizontal: 12, borderRadius: 12, backgroundColor: "#F0FAFC" },
  resultIcon: { width: 30, height: 30, borderRadius: 15, backgroundColor: "#13708D", alignItems: "center", justifyContent: "center", marginRight: 10 },
  resultTitle: { fontSize: 13, fontWeight: "700", color: "#1E293B", marginBottom: 3 },
  resultAddress: { fontSize: 11, lineHeight: 16, color: "#64748B" },
  settingRow: { flexDirection: "row", alignItems: "center" },
  settingIcon: { width: 38, height: 38, borderRadius: 12, backgroundColor: "#EAF8FC", alignItems: "center", justifyContent: "center", marginRight: 12 },
  settingTitle: { fontSize: 14, fontWeight: "700", color: "#1E293B" },
  settingDescription: { marginTop: 3, fontSize: 11, lineHeight: 16, color: "#64748B" },
  separator: { height: 1, backgroundColor: "#F1F5F9", marginVertical: 18 },
  bufferHeader: { flexDirection: "row", alignItems: "center" },
  chipRow: { flexDirection: "row", gap: 8, marginTop: 16 },
  chip: { flex: 1, height: 38, alignItems: "center", justifyContent: "center", borderRadius: 10, borderWidth: 1, borderColor: "#CBD5E1", backgroundColor: "#FFFFFF" },
  selectedChip: { borderColor: "#13708D", backgroundColor: "#13708D" },
  chipText: { fontSize: 12, fontWeight: "600", color: "#475569" },
  selectedChipText: { color: "#FFFFFF" },
  privacyRow: { flexDirection: "row", alignItems: "flex-start", paddingHorizontal: 5, marginBottom: 18 },
  privacyText: { flex: 1, marginLeft: 8, fontSize: 11, lineHeight: 16, color: "#64748B" },
  saveButton: { height: 52, borderRadius: 14, alignItems: "center", justifyContent: "center", backgroundColor: "#13708D" },
  saveButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
  disabledButton: { opacity: 0.55 },
  deleteButton: { height: 48, marginTop: 12, flexDirection: "row", alignItems: "center", justifyContent: "center" },
  deleteText: { marginLeft: 7, fontSize: 13, fontWeight: "600", color: "#EF4444" },
});

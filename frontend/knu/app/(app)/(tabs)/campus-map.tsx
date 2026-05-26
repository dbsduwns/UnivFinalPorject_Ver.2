import React, { useMemo, useRef, useState } from "react";
import { ActivityIndicator, Platform, StyleSheet, Text, View, Alert, TouchableOpacity, ScrollView, Animated, Dimensions } from "react-native";
import { WebView } from "react-native-webview";
import * as Location from "expo-location";
import { Navigation, Info, X, ChevronRight, ChevronLeft, CornerUpRight, CornerUpLeft, ArrowUp, Footprints } from "lucide-react-native";

import { AppScreenLayout } from "@/components/AppScreenLayout";
import { fetchPedestrianRoute } from "@/utils/mapUtils";

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const KAKAO_MAP_KEY = process.env.EXPO_PUBLIC_KAKAO_MAP_KEY?.trim();
const KAKAO_MAP_BASE_URL =
  process.env.EXPO_PUBLIC_KAKAO_MAP_BASE_URL?.trim() ?? "https://kangnam.ac.kr";

const CAMPUS_LOCATIONS = [
  { name: "본관", lat: 37.276089, lng: 127.133217 },
  { name: "샬롬관", lat: 37.274935, lng: 127.130040 },
  { name: "경천관", lat: 37.276534, lng: 127.133904 },
  { name: "우원관", lat: 37.275812, lng: 127.131700 },
  { name: "인사관", lat: 37.275355, lng: 127.130796 },
  { name: "예술관", lat: 37.276066, lng: 127.130845 },
  { name: "도서관", lat: 37.276518, lng: 127.132160 },
  { name: "승리관", lat: 37.274474, lng: 127.132467 },
  { name: "교육관", lat: 37.275335, lng: 127.133302 },
  { name: "천은관", lat: 37.275759, lng: 127.134297 },
  { name: "후생관", lat: 37.276921, lng: 127.133535 },
  { name: "이공관", lat: 37.277086, lng: 127.134147 },
  { name: "심전2관", lat: 37.278582, lng: 127.133742 },
  { name: "심전1관", lat: 37.278044, lng: 127.134401 },
];

function getWebOrigin() {
  if (Platform.OS !== "web") return KAKAO_MAP_BASE_URL;
  const location = globalThis.location;
  return location ? location.origin : KAKAO_MAP_BASE_URL;
}

function buildMapHtml(baseUrl: string) {
  const sdkUrl =
    "https://dapi.kakao.com/v2/maps/sdk.js" +
    `?appkey=${encodeURIComponent(KAKAO_MAP_KEY ?? "")}` +
    "&libraries=services,clusterer,drawing&autoload=false";

  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <base href="${baseUrl}/">
        <style>
          body, html, #map { width: 100%; height: 100%; margin: 0; padding: 0; background-color: #f3f4f6; }
          .custom-overlay {
            background: white; border: 2px solid #1aaedb; border-radius: 16px;
            padding: 5px 12px; font-size: 12px; font-weight: 700; color: #1aaedb;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2); white-space: nowrap;
          }
        </style>
      </head>
      <body>
        <div id="map"></div>
        <script>
          var map = null;
          var currentPolyline = null;
          var routeMarkers = [];

          function postToApp(type, message) {
            if (window.ReactNativeWebView) {
              window.ReactNativeWebView.postMessage(JSON.stringify({ type: type, message: message }));
            }
          }

          function clearRoute() {
            if (currentPolyline) {
              currentPolyline.setMap(null);
              currentPolyline = null;
            }
            routeMarkers.forEach(function(m) { m.setMap(null); });
            routeMarkers = [];
          }

          function handleMessage(event) {
            try {
              var data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
              
              if (data.type === "CENTER_MAP" && map) {
                map.panTo(new kakao.maps.LatLng(data.lat, data.lng));
              }

              if (data.type === "CLEAR_ROUTE" && map) {
                clearRoute();
              }

              if (data.type === "DRAW_ROUTE" && map) {
                clearRoute();
                
                var path = data.points.map(function(p) { return new kakao.maps.LatLng(p.lat, p.lng); });
                currentPolyline = new kakao.maps.Polyline({
                  path: path, strokeWeight: 7, strokeColor: "#1aaedb", strokeOpacity: 0.9
                });
                currentPolyline.setMap(map);

                // 안내 지점 마커 추가
                if (data.guidance && data.guidance.length > 0) {
                  data.guidance.forEach(function(g) {
                    var marker = new kakao.maps.Marker({
                      position: new kakao.maps.LatLng(g.lat, g.lng),
                      map: map,
                    });
                    routeMarkers.push(marker);
                    kakao.maps.event.addListener(marker, 'click', function() {
                      postToApp("GUIDANCE_CLICK", g.description);
                    });
                  });
                }

                var bounds = new kakao.maps.LatLngBounds();
                path.forEach(function(p) { bounds.extend(p); });
                map.setBounds(bounds, 80, 80, 80, 80);
              }
            } catch (err) {
              postToApp("ERROR", "JS 수신 에러: " + err.message);
            }
          }

          window.addEventListener("message", handleMessage);
          document.addEventListener("message", handleMessage);

          function renderMap() {
            kakao.maps.load(function() {
              var container = document.getElementById("map");
              map = new kakao.maps.Map(container, { center: new kakao.maps.LatLng(37.2757, 127.1325), level: 3 });

              ${JSON.stringify(CAMPUS_LOCATIONS)}.forEach(function(loc) {
                var markerPos = new kakao.maps.LatLng(loc.lat, loc.lng);
                var marker = new kakao.maps.Marker({ position: markerPos, map: map });
                new kakao.maps.CustomOverlay({ content: '<div class="custom-overlay">' + loc.name + '</div>', map: map, position: markerPos, yAnchor: 2.6 });
                kakao.maps.event.addListener(marker, 'click', function() {
                  postToApp("MARKER_CLICK", { lat: loc.lat, lng: loc.lng, name: loc.name });
                });
              });

              kakao.maps.event.addListener(map, 'click', function() {
                postToApp("MAP_CLICK", null);
              });
            });
          }

          var script = document.createElement("script");
          script.src = ${JSON.stringify(sdkUrl)};
          script.onload = renderMap;
          document.head.appendChild(script);
        </script>
      </body>
    </html>
  `;
}

type LocationData = { name: string; lat: number; lng: number };
type RouteData = { totalDistance: number; totalTime: number; instructions: {text: string, type: string}[] };

export default function CampusMapScreen() {
  const webViewRef = useRef<WebView>(null);
  const mapBaseUrl = getWebOrigin();
  const mapHtml = useMemo(() => buildMapHtml(mapBaseUrl), [mapBaseUrl]);

  const [selectedLoc, setSelectedLoc] = useState<LocationData | null>(null);
  const [routeData, setRouteData] = useState<RouteData | null>(null);
  const [isRouting, setIsRouting] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(true);

  const drawerAnim = useRef(new Animated.Value(0)).current;

  const toggleDrawer = (open: boolean) => {
    setIsDrawerOpen(open);
    Animated.timing(drawerAnim, {
      toValue: open ? 0 : -320,
      duration: 300,
      useNativeDriver: true,
    }).start();
  };

  const handleClearRoute = () => {
    setSelectedLoc(null);
    setRouteData(null);
    webViewRef.current?.postMessage(JSON.stringify({ type: "CLEAR_ROUTE" }));
  };

  const handleBackToInfo = () => {
    setRouteData(null);
    webViewRef.current?.postMessage(JSON.stringify({ type: "CLEAR_ROUTE" }));
    if (selectedLoc) {
      webViewRef.current?.postMessage(JSON.stringify({ type: "CENTER_MAP", ...selectedLoc }));
    }
  };

  const getInstructionIcon = (text: string) => {
    if (text.includes("우회전")) return <CornerUpRight color="#1aaedb" size={20} />;
    if (text.includes("좌회전")) return <CornerUpLeft color="#1aaedb" size={20} />;
    if (text.includes("횡단보도")) return <Footprints color="#1aaedb" size={20} />;
    return <ArrowUp color="#1aaedb" size={20} />;
  };

  const handleFindRoute = async () => {
    if (!selectedLoc) return;
    setIsRouting(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return setIsRouting(false);

      let startX = 127.1264; let startY = 37.2708; // 구갈동 주민센터 고정

      const features = await fetchPedestrianRoute(startX, startY, selectedLoc.lng, selectedLoc.lat);
      const points: { lat: number; lng: number }[] = [];
      const guidance: { lat: number, lng: number, description: string }[] = [];
      const instructions: {text: string, type: string}[] = [];
      let totalDistance = 0, totalTime = 0;

      features.forEach((f: any, i: number) => {
        if (i === 0) { totalDistance = f.properties.totalDistance; totalTime = f.properties.totalTime; }
        if (f.properties.description) instructions.push({ text: f.properties.description, type: f.properties.turnType || '0' });
        
        if (f.geometry.type === "Point") {
          const coord = f.geometry.coordinates;
          points.push({ lat: coord[1], lng: coord[0] });
          if (f.properties.description && !f.properties.description.includes("도착") && !f.properties.description.includes("출발")) {
            guidance.push({ lat: coord[1], lng: coord[0], description: f.properties.description });
          }
        } else {
          f.geometry.coordinates.forEach((c: any) => points.push({ lat: c[1], lng: c[0] }));
        }
      });

      setRouteData({ totalDistance, totalTime, instructions });
      webViewRef.current?.postMessage(JSON.stringify({ type: "DRAW_ROUTE", points, guidance }));
      toggleDrawer(true);
    } catch (e) { Alert.alert("오류", "길찾기 실패"); } finally { setIsRouting(false); }
  };

  const onMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === "MARKER_CLICK") {
        setSelectedLoc(data.message);
        setRouteData(null);
        webViewRef.current?.postMessage(JSON.stringify({ type: "CLEAR_ROUTE" }));
        webViewRef.current?.postMessage(JSON.stringify({ type: "CENTER_MAP", ...data.message }));
        toggleDrawer(true);
      } else if (data.type === "MAP_CLICK") {
        if (routeData) toggleDrawer(false);
      } else if (data.type === "GUIDANCE_CLICK") {
        Alert.alert("안내", data.message);
      }
    } catch (e) {}
  };

  return (
    <AppScreenLayout>
      <View style={styles.container}>
        <WebView
          ref={webViewRef}
          style={styles.webview}
          source={{ html: mapHtml, baseUrl: mapBaseUrl + "/" }}
          onMessage={onMessage}
        />

        {/* 미니 제어바 (드로어가 닫혔을 때) */}
        {!isDrawerOpen && selectedLoc && (
          <TouchableOpacity style={styles.miniBar} onPress={() => toggleDrawer(true)}>
            <ChevronRight color="white" size={24} />
            <Text style={styles.miniBarText}>{selectedLoc.name} 안내 재개</Text>
          </TouchableOpacity>
        )}

        {/* 사이드 드로어 UI */}
        {selectedLoc && (
          <Animated.View style={[
            styles.drawer,
            routeData ? styles.drawerFull : styles.drawerCompact,
            { transform: [{ translateX: drawerAnim }] }
          ]}>
            <View style={styles.drawerHeader}>
              {routeData && (
                <TouchableOpacity onPress={handleBackToInfo} style={{ marginRight: 8, marginTop: 2 }}>
                  <ChevronLeft color="#6b7280" size={24} />
                </TouchableOpacity>
              )}
              <View style={{ flex: 1 }}>
                <Text style={styles.drawerTitle} numberOfLines={1}>{selectedLoc.name}</Text>
                {routeData && (
                  <Text style={styles.drawerSub}>약 {Math.ceil(routeData.totalTime / 60)}분 ({routeData.totalDistance}m)</Text>
                )}
              </View>
              <TouchableOpacity onPress={handleClearRoute}>
                <X color="#6b7280" size={24} />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.drawerContent} showsVerticalScrollIndicator={false}>
              {!routeData ? (
                <View style={styles.initialActions}>
                  <TouchableOpacity style={styles.actionItem} onPress={handleFindRoute}>
                    <View style={styles.iconCircle}><Navigation color="#1aaedb" size={24} /></View>
                    <Text style={styles.actionText}>길찾기</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.actionItem} onPress={() => Alert.alert('정보', '건물 상세 정보입니다.')}>
                    <View style={styles.iconCircle}><Info color="#1aaedb" size={24} /></View>
                    <Text style={styles.actionText}>건물정보</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                routeData.instructions.map((inst, idx) => (
                  <View key={idx} style={styles.instructionRow}>
                    <View style={styles.iconCircleSmall}>{getInstructionIcon(inst.text)}</View>
                    <Text style={styles.instructionText}>{inst.text}</Text>
                  </View>
                ))
              )}
            </ScrollView>
            
            <TouchableOpacity style={styles.drawerCloseTab} onPress={() => toggleDrawer(!isDrawerOpen)}>
              {isDrawerOpen ? <ChevronLeft color="#9ca3af" size={20} /> : <ChevronRight color="#9ca3af" size={20} />}
            </TouchableOpacity>
          </Animated.View>
        )}
      </View>
    </AppScreenLayout>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  webview: { flex: 1 },
  drawer: {
    position: 'absolute', top: 20, left: 16, width: 280,
    backgroundColor: 'white', borderRadius: 20, padding: 20,
    shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 10, elevation: 10,
    zIndex: 100,
  },
  drawerFull: {
    bottom: 20,
  },
  drawerCompact: {
    height: 180,
  },
  drawerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 },
  drawerTitle: { fontSize: 20, fontWeight: '700', color: '#111827' },
  drawerSub: { fontSize: 14, color: '#6b7280', marginTop: 4 },
  drawerContent: { flex: 1 },
  initialActions: { flexDirection: 'row', gap: 24, marginTop: 10 },
  actionItem: { alignItems: 'center', gap: 8 },
  actionText: { fontSize: 14, fontWeight: '600', color: '#374151' },
  instructionRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20, gap: 12 },
  iconCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#f0f9ff', justifyContent: 'center', alignItems: 'center' },
  iconCircleSmall: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#f0f9ff', justifyContent: 'center', alignItems: 'center' },
  instructionText: { fontSize: 14, color: '#4b5563', flex: 1, lineHeight: 20 },
  drawerCloseTab: { position: 'absolute', right: -12, top: '50%', backgroundColor: 'white', width: 24, height: 48, borderRadius: 12, justifyContent: 'center', alignItems: 'center', elevation: 5, shadowColor: "#000", shadowOpacity: 0.1, shadowRadius: 4 },
  miniBar: { position: 'absolute', left: 16, top: 20, backgroundColor: '#1aaedb', flexDirection: 'row', alignItems: 'center', padding: 12, borderRadius: 30, gap: 8, elevation: 5, zIndex: 90 },
  miniBarText: { color: 'white', fontWeight: '700' }
});

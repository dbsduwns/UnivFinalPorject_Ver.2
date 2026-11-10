import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  AppState,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import * as Application from "expo-application";
import * as FileSystem from "expo-file-system/legacy";
import * as IntentLauncher from "expo-intent-launcher";
import * as SecureStore from "expo-secure-store";
import * as Updates from "expo-updates";
import { Download, RefreshCw, ShieldCheck, Smartphone } from "lucide-react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { checkAndroidAppUpdate } from "@/features/app-update/api/app-update";
import type { AppRelease } from "@/features/app-update/types";


const BRAND = "#13708D";
const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;
const DISMISSED_RELEASE_KEY = "knu_dismissed_app_release";
const APK_MIME_TYPE = "application/vnd.android.package-archive";
const FLAG_GRANT_READ_URI_PERMISSION = 1;
const FLAG_ACTIVITY_NEW_TASK = 0x10000000;

type Prompt =
  | { kind: "binary"; release: AppRelease; mandatory: boolean }
  | { kind: "ota" };

function installedVersionCode() {
  const parsed = Number.parseInt(Application.nativeBuildVersion ?? "0", 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function installedVersionName() {
  return Application.nativeApplicationVersion ?? "1.1.0";
}

export function AppUpdateManager() {
  const insets = useSafeAreaInsets();
  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [downloadedApkUri, setDownloadedApkUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastCheckedAt = useRef(0);
  const checking = useRef(false);

  const checkForUpdates = useCallback(async (force = false) => {
    if (__DEV__ || checking.current) return;
    const now = Date.now();
    if (!force && now - lastCheckedAt.current < CHECK_INTERVAL_MS) return;

    checking.current = true;
    lastCheckedAt.current = now;
    try {
      if (Platform.OS === "android") {
        try {
          const result = await checkAndroidAppUpdate(installedVersionCode());
          if (result.update_available && result.latest_release) {
            const dismissedVersion = await SecureStore.getItemAsync(DISMISSED_RELEASE_KEY);
            if (result.mandatory || dismissedVersion !== String(result.latest_release.version_code)) {
              setPrompt({
                kind: "binary",
                release: result.latest_release,
                mandatory: result.mandatory,
              });
              return;
            }
          }
        } catch {
          // 바이너리 버전 API가 일시적으로 실패해도 OTA 확인은 계속한다.
        }
      }

      if (Updates.isEnabled) {
        const update = await Updates.checkForUpdateAsync();
        if (update.isAvailable) {
          const fetched = await Updates.fetchUpdateAsync();
          if (fetched.isNew) setPrompt({ kind: "ota" });
        }
      }
    } catch {
      // 자동 확인 실패는 앱 사용을 막지 않고 다음 주기에 다시 시도한다.
    } finally {
      checking.current = false;
    }
  }, []);

  useEffect(() => {
    void checkForUpdates(true);
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active") void checkForUpdates();
    });
    return () => subscription.remove();
  }, [checkForUpdates]);

  const closeOptionalUpdate = async () => {
    if (!prompt) return;
    if (prompt.kind === "ota") {
      setPrompt(null);
      setError(null);
      return;
    }
    if (prompt.mandatory) return;
    await SecureStore.setItemAsync(DISMISSED_RELEASE_KEY, String(prompt.release.version_code));
    setPrompt(null);
    setError(null);
  };

  const openUnknownSourcesSettings = async () => {
    if (!Application.applicationId) return;
    await IntentLauncher.startActivityAsync(
      IntentLauncher.ActivityAction.MANAGE_UNKNOWN_APP_SOURCES,
      { data: `package:${Application.applicationId}` },
    );
  };

  const launchApkInstaller = async (fileUri: string) => {
    const contentUri = await FileSystem.getContentUriAsync(fileUri);
    await IntentLauncher.startActivityAsync("android.intent.action.VIEW", {
      data: contentUri,
      type: APK_MIME_TYPE,
      flags: FLAG_GRANT_READ_URI_PERMISSION | FLAG_ACTIVITY_NEW_TASK,
    });
  };

  const installBinaryUpdate = async () => {
    if (!prompt || prompt.kind !== "binary" || Platform.OS !== "android") return;
    setError(null);

    try {
      if (downloadedApkUri) {
        await launchApkInstaller(downloadedApkUri);
        return;
      }

      if (!FileSystem.cacheDirectory) {
        throw new Error("업데이트 파일 저장소를 사용할 수 없습니다.");
      }

      setDownloading(true);
      setDownloadProgress(0);
      const targetUri = `${FileSystem.cacheDirectory}knu-campus-${prompt.release.version_code}.apk`;
      await FileSystem.deleteAsync(targetUri, { idempotent: true });
      const task = FileSystem.createDownloadResumable(
        prompt.release.apk_url,
        targetUri,
        {},
        ({ totalBytesWritten, totalBytesExpectedToWrite }) => {
          if (totalBytesExpectedToWrite > 0) {
            setDownloadProgress(totalBytesWritten / totalBytesExpectedToWrite);
          }
        },
      );
      const result = await task.downloadAsync();
      if (!result || result.status < 200 || result.status >= 300) {
        throw new Error("업데이트 APK 다운로드에 실패했습니다.");
      }
      setDownloadedApkUri(result.uri);
      setDownloadProgress(1);
      await launchApkInstaller(result.uri);
    } catch {
      setError("설치 화면을 열지 못했습니다. 이 앱의 ‘알 수 없는 앱 설치’를 허용한 뒤 다시 시도해 주세요.");
    } finally {
      setDownloading(false);
    }
  };

  const applyOtaUpdate = async () => {
    setError(null);
    try {
      await Updates.reloadAsync();
    } catch {
      setError("업데이트를 적용하지 못했습니다. 앱을 완전히 종료한 뒤 다시 실행해 주세요.");
    }
  };

  if (!prompt) return null;

  const isBinary = prompt.kind === "binary";
  const release = isBinary ? prompt.release : null;
  const mandatory = isBinary && prompt.mandatory;

  return (
    <Modal
      transparent
      visible
      animationType="fade"
      statusBarTranslucent
      navigationBarTranslucent={false}
      onRequestClose={() => { if (!mandatory) void closeOptionalUpdate(); }}
    >
      <View className="flex-1 bg-black/50 justify-end sm:justify-center sm:items-center">
        <View
          className="bg-white rounded-t-[28px] sm:rounded-[28px] px-6 pt-7 sm:w-[440px] sm:max-w-[90%]"
          style={{ paddingBottom: Math.max(insets.bottom + 16, 32) }}
        >
          <View className="w-14 h-14 rounded-2xl bg-cyan-50 items-center justify-center">
            {isBinary ? <Download size={28} color={BRAND} /> : <RefreshCw size={28} color={BRAND} />}
          </View>

          <Text className="mt-5 text-2xl font-extrabold text-gray-900">
            {mandatory ? "필수 업데이트가 필요합니다" : "새 업데이트가 있습니다"}
          </Text>
          <Text className="mt-2 text-sm leading-6 text-gray-600">
            {isBinary
              ? `KNU Campus ${release?.version_name} 버전을 설치할 수 있습니다.`
              : "새로운 화면과 기능을 다운로드했습니다. 앱을 다시 시작하면 바로 적용됩니다."}
          </Text>

          {isBinary && (
            <View className="mt-4 px-4 py-3 rounded-2xl bg-gray-50 flex-row items-center">
              <Smartphone size={20} color="#64748B" />
              <Text className="ml-3 text-sm font-bold text-gray-700">
                현재 {installedVersionName()} → 최신 {release?.version_name}
              </Text>
            </View>
          )}

          {!!release?.release_notes.length && (
            <ScrollView className="mt-4 max-h-40" showsVerticalScrollIndicator={false}>
              {release.release_notes.map((note, index) => (
                <View key={`${index}-${note}`} className="flex-row mb-2">
                  <View className="w-1.5 h-1.5 rounded-full bg-[#13708D] mt-2 mr-2" />
                  <Text className="flex-1 text-sm leading-5 text-gray-600">{note}</Text>
                </View>
              ))}
            </ScrollView>
          )}

          {downloading && (
            <View className="mt-5">
              <View className="h-2 rounded-full bg-gray-200 overflow-hidden">
                <View
                  className="h-full bg-[#13708D] rounded-full"
                  style={{ width: `${Math.max(3, Math.round(downloadProgress * 100))}%` }}
                />
              </View>
              <Text className="mt-2 text-xs text-center text-gray-500">
                업데이트 다운로드 중 {Math.round(downloadProgress * 100)}%
              </Text>
            </View>
          )}

          {!!error && (
            <View className="mt-4 p-3 rounded-xl bg-red-50">
              <Text className="text-sm leading-5 text-red-700">{error}</Text>
              {isBinary && (
                <Pressable onPress={() => { void openUnknownSourcesSettings(); }} className="mt-2">
                  <Text className="text-sm font-extrabold text-red-700">설치 권한 설정 열기</Text>
                </Pressable>
              )}
            </View>
          )}

          <Pressable
            disabled={downloading}
            onPress={() => { void (isBinary ? installBinaryUpdate() : applyOtaUpdate()); }}
            className="mt-6 h-14 rounded-2xl bg-[#13708D] flex-row items-center justify-center disabled:opacity-60"
          >
            {downloading ? (
              <ActivityIndicator color="white" />
            ) : (
              <>
                <ShieldCheck size={20} color="white" />
                <Text className="ml-2 text-base font-extrabold text-white">
                  {isBinary ? (downloadedApkUri ? "설치 화면 다시 열기" : "다운로드 및 설치") : "지금 다시 시작"}
                </Text>
              </>
            )}
          </Pressable>

          {!mandatory && (
            <Pressable onPress={() => { void closeOptionalUpdate(); }} className="h-12 items-center justify-center">
              <Text className="text-sm font-bold text-gray-500">나중에</Text>
            </Pressable>
          )}
        </View>
      </View>
    </Modal>
  );
}

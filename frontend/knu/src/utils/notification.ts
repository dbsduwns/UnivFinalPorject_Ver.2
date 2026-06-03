import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform } from "react-native";
import Constants from "expo-constants";
import { apiClient } from "@/api/client";

export async function registerForPushNotificationsAsync() {
  if (!Device.isDevice) {
    console.log("Must use physical device for Push Notifications");
    return;
  }

  // Expo SDK 53+ 부터 Expo Go 앱(Android)에서 원격 푸시 알림이 지원되지 않음
  // 이로 인한 런타임 에러 방지를 위해 Expo Go 환경 체크
  const isExpoGo = Constants.appOwnership === 'expo';
  if (isExpoGo && Platform.OS === 'android') {
    console.warn("Push notifications (remote) are not supported in Expo Go on Android. Use a development build.");
    return;
  }

  let token;

  try {
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("default", {
        name: "default",
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: "#FF231F7C",
      });
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== "granted") {
      console.log("Failed to get push token for push notification!");
      return;
    }
    
    const projectId = Constants.expoConfig?.extra?.eas?.projectId || Constants.easConfig?.projectId;
    if (!projectId) {
      console.warn("Project ID not found. Push tokens may not be fetched correctly.");
    }
    
    token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
    console.log("Push token fetched:", token);
  } catch (e) {
    console.error("Error during push notification registration:", e);
  }

  return token;
}

export async function sendPushTokenToServer(token: string) {
  try {
    await apiClient.put("/auth/notification-token", { expo_push_token: token });
  } catch (error) {
    console.error("Failed to send push token to server:", error);
  }
}

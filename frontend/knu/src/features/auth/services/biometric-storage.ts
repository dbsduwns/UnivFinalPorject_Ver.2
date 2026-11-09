import * as SecureStore from "expo-secure-store";

const BIOMETRIC_ENABLED_KEY = "knu_biometric_login_enabled";

export async function isBiometricLoginEnabled(): Promise<boolean> {
  return (await SecureStore.getItemAsync(BIOMETRIC_ENABLED_KEY)) === "true";
}

export async function setBiometricLoginEnabled(enabled: boolean): Promise<void> {
  if (enabled) {
    await SecureStore.setItemAsync(BIOMETRIC_ENABLED_KEY, "true");
  } else {
    await SecureStore.deleteItemAsync(BIOMETRIC_ENABLED_KEY);
  }
}


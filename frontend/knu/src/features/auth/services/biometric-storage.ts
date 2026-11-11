import * as SecureStore from "expo-secure-store";
import * as Crypto from "expo-crypto";

const BIOMETRIC_ENABLED_KEY = "knu_biometric_login_enabled";
const BIOMETRIC_CREDENTIAL_KEY = "knu_biometric_credential";
const BIOMETRIC_DEVICE_ID_KEY = "knu_biometric_device_id";

const protectedOptions: SecureStore.SecureStoreOptions = {
  requireAuthentication: true,
};

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

export async function createCredential(): Promise<string> {
  const bytes = await Crypto.getRandomBytesAsync(32);
  return bytesToHex(bytes);
}

export async function getOrCreateDeviceId(): Promise<string> {
  const existing = await SecureStore.getItemAsync(BIOMETRIC_DEVICE_ID_KEY);
  if (existing) return existing;

  const bytes = await Crypto.getRandomBytesAsync(16);
  const deviceId = bytesToHex(bytes);
  await SecureStore.setItemAsync(BIOMETRIC_DEVICE_ID_KEY, deviceId);
  return deviceId;
}

export async function setCredential(credential: string): Promise<void> {
  await SecureStore.setItemAsync(BIOMETRIC_CREDENTIAL_KEY, credential, protectedOptions);
}

export async function getCredential(): Promise<string | null> {
  return SecureStore.getItemAsync(BIOMETRIC_CREDENTIAL_KEY, protectedOptions);
}

export async function clearBiometricData(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(BIOMETRIC_ENABLED_KEY),
    SecureStore.deleteItemAsync(BIOMETRIC_CREDENTIAL_KEY),
    SecureStore.deleteItemAsync(BIOMETRIC_DEVICE_ID_KEY),
  ]);
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}


import * as SecureStore from "expo-secure-store";

const ONBOARDING_TOKEN_KEY = "knu_google_onboarding_token";
const ONBOARDING_EXPIRES_AT_KEY = "knu_google_onboarding_expires_at";

export type PendingOnboarding = {
  onboardingToken: string;
  expiresAt: string;
};

export async function getPendingOnboarding(): Promise<PendingOnboarding | null> {
  const [onboardingToken, expiresAt] = await Promise.all([
    SecureStore.getItemAsync(ONBOARDING_TOKEN_KEY),
    SecureStore.getItemAsync(ONBOARDING_EXPIRES_AT_KEY),
  ]);

  if (!onboardingToken || !expiresAt) return null;

  if (new Date(expiresAt).getTime() <= Date.now()) {
    await clearPendingOnboarding();
    return null;
  }

  return { onboardingToken, expiresAt };
}

export async function setPendingOnboarding(
  onboardingToken: string,
  expiresAt: string,
): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ONBOARDING_TOKEN_KEY, onboardingToken),
    SecureStore.setItemAsync(ONBOARDING_EXPIRES_AT_KEY, expiresAt),
  ]);
}

export async function clearPendingOnboarding(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ONBOARDING_TOKEN_KEY),
    SecureStore.deleteItemAsync(ONBOARDING_EXPIRES_AT_KEY),
  ]);
}

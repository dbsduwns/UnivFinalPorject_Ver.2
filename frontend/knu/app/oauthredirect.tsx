import { ActivityIndicator, View } from "react-native";
import { Redirect } from "expo-router";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/features/auth/store/auth-store";
import * as onboardingStorage from "@/features/auth/services/onboarding-storage";

/**
 * Native Google OAuth callback route.
 * expo-auth-session consumes the callback parameters; this route only prevents
 * Expo Router from displaying an unmatched-route screen for /oauthredirect.
 */
export default function OAuthRedirectRoute() {
  const ready = useAuthStore((state) => state.ready);
  const user = useAuthStore((state) => state.user);
  const pendingOnboarding = useAuthStore((state) => state.pendingOnboarding);
  const [checkingOnboarding, setCheckingOnboarding] = useState(true);
  const [storedPendingOnboarding, setStoredPendingOnboarding] = useState<
    Awaited<ReturnType<typeof onboardingStorage.getPendingOnboarding>>
  >(null);

  useEffect(() => {
    let mounted = true;

    const waitForOnboarding = async () => {
      // The AuthSession response and the callback route can be processed in
      // adjacent render cycles. Give googleLogin time to persist the pending
      // onboarding session before falling back to the login screen.
      for (let attempt = 0; attempt < 20 && mounted; attempt += 1) {
        const pending = await onboardingStorage.getPendingOnboarding();
        if (pending) {
          if (mounted) setStoredPendingOnboarding(pending);
          break;
        }
        if (useAuthStore.getState().user) break;
        await new Promise((resolve) => setTimeout(resolve, 100));
      }

      if (mounted) setCheckingOnboarding(false);
    };

    void waitForOnboarding();
    return () => {
      mounted = false;
    };
  }, []);

  if (!ready || checkingOnboarding) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator />
      </View>
    );
  }

  if (user) {
    return <Redirect href="/(app)/(tabs)" />;
  }

  const onboarding = pendingOnboarding ?? storedPendingOnboarding;

  if (onboarding) {
    return (
      <Redirect
        href={{
          pathname: "/student-verification",
          params: { onboardingToken: onboarding.onboardingToken },
        }}
      />
    );
  }

  return <Redirect href="/(auth)/login" />;
}

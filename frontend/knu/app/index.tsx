import { Redirect } from "expo-router";

import { hrefAppHome, hrefBiometricLogin, hrefLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";

/** `/` — 세션 상태에 따라 탭 또는 로그인으로 보낸다. */
export default function EntryScreen() {
  const ready = useAuthStore((s) => s.ready);
  const user = useAuthStore((s) => s.user);
  const pendingOnboarding = useAuthStore((s) => s.pendingOnboarding);
  const biometricRequired = useAuthStore((s) => s.biometricRequired);

  if (!ready) {
    return null;
  }

  if (user) {
    return <Redirect href={hrefAppHome} />;
  }

  if (biometricRequired) {
    return <Redirect href={hrefBiometricLogin as never} />;
  }

  if (pendingOnboarding) {
    return (
      <Redirect
        href={{
          pathname: "/student-verification",
          params: { onboardingToken: pendingOnboarding.onboardingToken },
        }}
      />
    );
  }

  return <Redirect href={hrefLogin} />;
}

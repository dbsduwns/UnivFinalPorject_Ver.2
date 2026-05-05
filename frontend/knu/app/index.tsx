import { Redirect } from "expo-router";

import { hrefAppHome, hrefLogin } from "@/constants/routes";
import { useAuthStore } from "@/features/auth/store/auth-store";

/** `/` — 세션 상태에 따라 탭 또는 로그인으로 보낸다. */
export default function EntryScreen() {
  const ready = useAuthStore((s) => s.ready);
  const user = useAuthStore((s) => s.user);

  if (!ready) {
    return null;
  }

  if (user) {
    return <Redirect href={hrefAppHome} />;
  }

  return <Redirect href={hrefLogin} />;
}

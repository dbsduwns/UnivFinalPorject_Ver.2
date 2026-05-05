import { isAxiosError } from "axios";

/** 개발 모드에서 Axios 오류를 한 줄로 로깅한다. `response`가 없으면 네트워크/연결 문제다. */
export function logDevAxiosError(scope: string, err: unknown): void {
  if (!__DEV__) return;
  if (!isAxiosError(err)) {
    console.warn(`[${scope}]`, err);
    return;
  }
  if (err.response) {
    console.warn(`[${scope}]`, err.response.status, err.response.data);
    return;
  }
  console.warn(`[${scope}] 네트워크 오류 (응답 없음)`, {
    message: err.message,
    code: err.code,
    baseURL: err.config?.baseURL,
    path: err.config?.url,
  });
}

export function getAxiosErrorMessage(
  err: unknown,
  fallback = "요청에 실패했습니다."
): string {
  if (!isAxiosError(err)) return fallback;
  if (!err.response) {
    return "서버에 연결할 수 없습니다. PC에서 백엔드가 켜져 있는지, EXPO_PUBLIC_API_URL(실기기는 PC IP, Android 에뮬은 10.0.2.2)을 확인하세요.";
  }
  const raw = err.response?.data;
  if (typeof raw === "string" && raw.trim()) return raw;

  const data = raw as { detail?: unknown; message?: unknown } | undefined;
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((item) => {
      if (typeof item === "object" && item !== null && "msg" in item) {
        return String((item as { msg: string }).msg);
      }
      return String(item);
    });
    return msgs.join("\n") || fallback;
  }
  if (typeof data?.message === "string") return data.message;
  return fallback;
}

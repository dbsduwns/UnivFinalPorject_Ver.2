const raw = process.env.EXPO_PUBLIC_API_URL?.trim();

if (!raw) {
  throw new Error("EXPO_PUBLIC_API_URL이 설정되지 않았습니다.");
}

/** 백엔드 API 베이스 URL (끝의 `/` 제거). */
export const API_BASE_URL = raw.replace(/\/+$/, "");

/** 전시 환경에서는 외부 AI 서비스 없이 대표 질문을 로컬 답변으로 시연합니다. */
export const IS_EXHIBITION_MODE =
  process.env.EXPO_PUBLIC_EXHIBITION_MODE?.trim().toLowerCase() === "true";

console.log("ENV =", process.env.EXPO_PUBLIC_API_URL);
console.log("BASE =", API_BASE_URL);

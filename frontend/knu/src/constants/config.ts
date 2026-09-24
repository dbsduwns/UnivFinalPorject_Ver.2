const raw = process.env.EXPO_PUBLIC_API_URL?.trim();

if (!raw) {
  throw new Error("EXPO_PUBLIC_API_URL이 설정되지 않았습니다.");
}

/** 백엔드 API 베이스 URL (끝의 `/` 제거). */
export const API_BASE_URL = raw.replace(/\/+$/, "");

console.log("ENV =", process.env.EXPO_PUBLIC_API_URL);
console.log("BASE =", API_BASE_URL);

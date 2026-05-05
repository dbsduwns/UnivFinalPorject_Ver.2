const raw = process.env.EXPO_PUBLIC_API_URL?.trim();

/** 백엔드 API 베이스 URL (끝의 `/` 제거). 실기기/에뮬에서 PC의 API에 붙이려면 EXPO_PUBLIC_API_URL을 본인 환경에 맞게 설정. */
export const API_BASE_URL = (raw && raw.length > 0 ? raw : "http://127.0.0.1:8000").replace(
  /\/$/,
  ""
);

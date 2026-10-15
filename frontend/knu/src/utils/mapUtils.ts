export const fetchPedestrianRoute = async (
  startX: number,
  startY: number,
  endX: number,
  endY: number,
) => {
  const TMAP_KEY = process.env.EXPO_PUBLIC_TMAP_KEY || "";
  if (!TMAP_KEY) {
    throw new Error("TMAP_API_KEY is missing in .env");
  }

  const url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&format=json";

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      appKey: TMAP_KEY,
    },
    body: JSON.stringify({
      startX,
      startY,
      endX,
      endY,
      startName: "내 위치",
      endName: "목적지",
    }),
  });

  const responseBody = await response.text();

  if (!response.ok) {
    let message = responseBody;

    try {
      const errorData = JSON.parse(responseBody);
      message = errorData.error?.message || errorData.message || responseBody;
    } catch {
      // JSON이 아닌 응답이면 응답 원문을 사용합니다.
    }

    throw new Error(
      `Tmap API Error (${response.status} ${response.statusText}): ${message || "응답 본문 없음"}`,
    );
  }

  let data: any;
  try {
    data = JSON.parse(responseBody);
  } catch {
    throw new Error(`Tmap API 응답이 JSON 형식이 아닙니다: ${responseBody.slice(0, 500)}`);
  }

  if (!Array.isArray(data.features)) {
    throw new Error(`Tmap API 응답에 features가 없습니다: ${responseBody.slice(0, 500)}`);
  }

  return data.features;
};

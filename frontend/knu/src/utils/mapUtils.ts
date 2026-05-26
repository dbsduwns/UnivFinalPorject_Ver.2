export const fetchPedestrianRoute = async (
  startX: number,
  startY: number,
  endX: number,
  endY: number,
) => {
  const TMAP_KEY = process.env.EXPO_PUBLIC_TMAP_API_KEY || "";
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

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(`Tmap API Error: ${errorData.error?.message || response.statusText}`);
  }

  const data = await response.json();
  return data.features;
};

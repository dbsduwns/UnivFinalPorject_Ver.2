const API = (window.DOWNLOAD_API_URL || "").replace(/\/+$/, "");
const pageUrl = window.location.origin + window.location.pathname.replace(/index\.html$/, "");
const $ = (selector) => document.querySelector(selector);

function formatDate(value) {
  if (!value) return "";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "" : `게시일 ${parsed.toLocaleDateString("ko-KR")}`;
}

function setupQrCode() {
  const qr = $("#qr-code");
  const encodedUrl = encodeURIComponent(pageUrl);
  qr.src = `https://api.qrserver.com/v1/create-qr-code/?size=320x320&margin=12&data=${encodedUrl}`;
  qr.onload = () => { $("#qr-status").textContent = "이 페이지 주소를 담은 QR코드입니다."; };
  qr.onerror = () => { $("#qr-status").textContent = "QR코드를 불러오지 못했습니다. 아래 다운로드 버튼을 이용해 주세요."; };
}

async function loadRelease() {
  if (!API) throw new Error("다운로드 API 주소가 설정되지 않았습니다.");
  const response = await fetch(`${API}/api/app-updates/android?current_version_code=0`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error("최신 APK 정보를 불러오지 못했습니다.");
  const data = await response.json();
  if (!data.latest_release) throw new Error("현재 등록된 APK가 없습니다.");

  const release = data.latest_release;
  $("#release-card").hidden = false;
  $("#release-status").textContent = "최신 버전을 준비했습니다.";
  $("#version-name").textContent = release.version_name;
  $("#version-code").textContent = `versionCode ${release.version_code}`;
  $("#published-at").textContent = formatDate(release.published_at || release.created_at);
  $("#download-button").href = release.apk_url;
  $("#release-notes").innerHTML = (release.release_notes || []).map(note => `<li>${escapeHtml(note)}</li>`).join("");
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
}

setupQrCode();
loadRelease().catch((error) => {
  $("#release-status").hidden = true;
  $("#error-message").hidden = false;
  $("#error-message").textContent = error.message;
});

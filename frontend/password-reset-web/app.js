const API_BASE_URL = (window.PASSWORD_RESET_API_URL || "").replace(/\/+$/, "");
const token = new URLSearchParams(window.location.search).get("token")?.trim() || "";
const form = document.querySelector("#reset-form");
const submitButton = document.querySelector("#submit-button");
const message = document.querySelector("#message");
const invalidTokenNotice = document.querySelector("#invalid-token");

if (!token) {
  invalidTokenNotice.hidden = false;
  form.hidden = true;
}

function showMessage(text, kind) {
  message.textContent = text;
  message.className = `notice notice-${kind}`;
  message.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.hidden = true;

  if (!API_BASE_URL) {
    showMessage("서비스 설정이 완료되지 않았습니다. 잠시 후 다시 시도해 주세요.", "error");
    return;
  }

  const newPassword = document.querySelector("#new-password").value;
  const confirmPassword = document.querySelector("#confirm-password").value;

  if (newPassword.length < 8) {
    showMessage("비밀번호는 8자 이상이어야 합니다.", "error");
    return;
  }
  if (new TextEncoder().encode(newPassword).length > 72 || new TextEncoder().encode(confirmPassword).length > 72) {
    showMessage("비밀번호는 UTF-8 기준 72바이트 이하여야 합니다.", "error");
    return;
  }
  if (newPassword !== confirmPassword) {
    showMessage("비밀번호가 서로 일치하지 않습니다.", "error");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "변경 중...";

  try {
    const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ token, new_password: newPassword, confirm_password: confirmPassword }),
    });

    if (response.status === 204) {
      form.hidden = true;
      showMessage("비밀번호가 변경되었습니다. 앱에서 새 비밀번호로 로그인해 주세요.", "success");
      return;
    }

    let detail = "링크가 만료되었거나 이미 사용되었습니다. 재설정 이메일을 다시 요청해 주세요.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch { /* Some errors have no JSON response body. */ }
    showMessage(detail, "error");
  } catch {
    showMessage("서버에 연결하지 못했습니다. 인터넷 연결을 확인하고 다시 시도해 주세요.", "error");
  } finally {
    if (!form.hidden) {
      submitButton.disabled = false;
      submitButton.textContent = "비밀번호 변경";
    }
  }
});

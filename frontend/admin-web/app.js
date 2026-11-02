const API = (window.ADMIN_API_URL || "").replace(/\/+$/, "");
const state = { token: sessionStorage.getItem("knu_admin_token"), user: null, view: "dashboard" };
const $ = (s) => document.querySelector(s);
const esc = (v = "") => String(v).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const date = (v) => v ? new Date(v).toLocaleString("ko-KR") : "-";

async function request(path, options = {}) {
  if (!API) throw new Error("관리자 API 주소가 설정되지 않았습니다.");
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 15000);
  let r;
  try {
    r = await fetch(`${API}${path}`, { ...options, headers, signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") throw new Error("서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.");
    throw new Error("서버에 연결하지 못했습니다. 관리자 API 주소와 네트워크 상태를 확인해 주세요.");
  } finally {
    window.clearTimeout(timer);
  }
  if (!r.ok) { const body = await r.json().catch(() => ({})); throw new Error(body.detail || "요청을 처리하지 못했습니다."); }
  if (r.status === 204) return null;
  return r.json().catch(() => null);
}
function flash(message, error = false) { const node = $("#flash"); node.className = `flash${error ? " error" : ""}`; node.textContent = message; setTimeout(() => { if (node.textContent === message) node.textContent = ""; }, 4500); }
function button(label, attrs = "") { return `<button ${attrs}>${label}</button>`; }
function openModal(title, body) { $("#modal-content").innerHTML = `<div class="modal-body"><div class="modal-head"><h2>${title}</h2><button class="secondary" onclick="closeModal()">닫기</button></div>${body}</div>`; $("#modal").showModal(); }
function closeModal() { $("#modal").close(); }
window.closeModal = closeModal;

const menus = [
  ["dashboard", "▦", "대시보드"], ["notices", "▣", "공지사항"], ["community", "⚑", "커뮤니티"], ["data", "↻", "서비스 데이터"], ["users", "♙", "회원 관리"]
];
const paths = { dashboard: "/dashboard", notices: "/notices", community: "/community", data: "/data", users: "/users" };
function viewFromPath() {
  const segment = window.location.pathname.split("/").filter(Boolean)[0];
  return Object.hasOwn(paths, segment) ? segment : "dashboard";
}
function goTo(view, replace = false) {
  const path = paths[view] || paths.dashboard;
  if (window.location.pathname !== path) {
    window.history[replace ? "replaceState" : "pushState"]({ view }, "", path);
  }
  renderView(view);
}
function renderNav() { $("#nav").innerHTML = menus.map(([key, icon, label]) => `<button class="${key === state.view ? "active" : ""}" data-view="${key}"><span>${icon}</span>${label}</button>`).join(""); $("#nav").onclick = e => { const b = e.target.closest("button[data-view]"); if (b) navigate(b.dataset.view); }; }
async function renderView(view) { state.view = view; renderNav(); const label = menus.find(x => x[0] === view)[2]; $("#page-title").textContent = label; $("#content").innerHTML = `<div class="empty">불러오는 중…</div>`; try { await ({ dashboard, notices, community, data, users }[view])(); } catch (e) { $("#content").innerHTML = `<div class="card empty">${esc(e.message)}</div>`; } }
function navigate(view) { goTo(view); }

async function dashboard() {
  const d = await request("/api/admin/dashboard");
  $("#content").innerHTML = `<div class="grid stats">${[["전체 회원",d.total_users],["활성 회원",d.active_users],["게시글",d.total_posts],["미처리 신고",d.pending_reports]].map(([l,n])=>`<div class="card stat"><div class="label">${l}</div><div class="number">${n}</div></div>`).join("")}</div><div class="grid split" style="margin-top:16px"><section class="card"><h3>주요 관리 메뉴</h3><div class="quick"><button data-go="notices">공지사항 관리<br><small>등록·수정·크롤링</small></button><button data-go="community">커뮤니티 관리<br><small>게시글·신고 모더레이션</small></button><button data-go="data">서비스 데이터<br><small>크롤링·강의 등록</small></button><button data-go="users">회원 관리<br><small>권한·계정 상태</small></button></div></section><section class="card"><h3>최근 신고 상태</h3>${d.recent_reports.length ? d.recent_reports.map(r=>`<div class="result"><b>#${r.id} · ${esc(r.status)}</b><br>${esc(r.content_snapshot).slice(0,90)}<br><span class="small">${date(r.created_at)}</span></div>`).join("") : `<p class="muted">최근 신고가 없습니다.</p>`}</section></div>`;
  $("#content").querySelectorAll("[data-go]").forEach(b => b.onclick = () => navigate(b.dataset.go));
}

async function notices() {
  const load = async () => { const keyword = $("#notice-query").value.trim(); const rows = await request(`/api/notices/${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`); $("#notice-rows").innerHTML = rows.length ? rows.map(n=>`<tr><td>${n.id}</td><td class="wrap"><b>${esc(n.title)}</b><br><span class="small">${esc(n.category)}</span></td><td>${n.is_important ? `<span class="badge">중요</span>` : "-"}</td><td>${date(n.published_at || n.crawled_at)}</td><td class="actions"><button data-edit="${n.id}">수정</button><button class="danger" data-delete="${n.id}">삭제</button></td></tr>`).join("") : `<tr><td colspan="5" class="empty">공지사항이 없습니다.</td></tr>`; $("#notice-rows").onclick = async e => { const id = e.target.dataset.edit || e.target.dataset.delete; if (!id) return; if (e.target.dataset.delete) { if (confirm("이 공지를 삭제할까요?")) { await request(`/api/notices/${id}`, {method:"DELETE"}); flash("공지를 삭제했습니다."); load(); } return; } const n = rows.find(x=>x.id === Number(id)); noticeForm(n); }; };
  $("#content").innerHTML = `<div class="toolbar"><input id="notice-query" placeholder="제목 또는 내용 검색"><button id="notice-search" class="secondary">검색</button><button id="notice-new">공지 등록</button><button id="notice-crawl" class="secondary">학교 공지 크롤링</button></div><div class="card table-wrap"><table class="table"><thead><tr><th>ID</th><th>제목</th><th>상태</th><th>게시일</th><th></th></tr></thead><tbody id="notice-rows"></tbody></table></div>`;
  $("#notice-search").onclick = load; $("#notice-new").onclick = () => noticeForm(); $("#notice-crawl").onclick = async () => { $("#notice-crawl").disabled=true; try { const r=await request("/api/notices/crawl",{method:"POST"}); flash(`${r.count ?? 0}건의 학교 공지를 수집했습니다.`); load(); } finally { $("#notice-crawl").disabled=false; } }; load();
}
function noticeForm(n = null) { openModal(n ? "공지 수정" : "공지 등록", `<form id="notice-form" class="form-grid"><label class="wide">제목<input name="title" required value="${esc(n?.title)}"></label><label>분류<input name="category" required value="${esc(n?.category || "학사")}"></label><label>중요 공지<select name="important"><option value="false">일반</option><option value="true" ${n?.is_important ? "selected" : ""}>중요</option></select></label><label class="wide">내용<textarea name="content" required>${esc(n?.content || "")}</textarea></label><div class="wide modal-actions"><button type="button" class="secondary" onclick="closeModal()">취소</button><button>저장</button></div></form>`); $("#notice-form").onsubmit = async e => { e.preventDefault(); const f = new FormData(e.target), body={title:f.get("title").trim(),category:f.get("category").trim(),content:f.get("content").trim(),is_important:f.get("important")==="true"}; await request(n?`/api/notices/${n.id}`:"/api/notices/",{method:n?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}); closeModal(); flash("공지를 저장했습니다."); notices(); }; }

async function community() {
  const loadPosts = async () => { const q=$("#post-query").value.trim(); const rows=await request(`/api/admin/community/posts?limit=100${q?`&keyword=${encodeURIComponent(q)}`:""}`); $("#post-rows").innerHTML=rows.length?rows.map(p=>`<tr><td>${esc(p.board_slug)}</td><td class="wrap"><b>${esc(p.title)}</b><br><span class="small">${esc(p.author_name)} · ${date(p.created_at)}</span></td><td>${p.is_hidden?'<span class="badge off">숨김</span>':'공개'}</td><td><button data-post="${esc(p.slug)}">상세·수정</button></td></tr>`).join(""):`<tr><td colspan="4" class="empty">게시글이 없습니다.</td></tr>`; $("#post-rows").onclick=e=>{const s=e.target.dataset.post;if(s)postDetail(s);}; };
  $("#content").innerHTML=`<div class="toolbar"><input id="post-query" placeholder="게시글 제목·내용 검색"><button id="post-search" class="secondary">검색</button><button id="reports">댓글 신고 목록</button><button id="blocks" class="secondary">사용자 차단 현황</button></div><div class="card table-wrap"><table class="table"><thead><tr><th>게시판</th><th>게시글</th><th>공개</th><th></th></tr></thead><tbody id="post-rows"></tbody></table></div>`; $("#post-search").onclick=loadPosts; $("#reports").onclick=reports; $("#blocks").onclick=blocks; loadPosts();
}
async function postDetail(slug) { const p=await request(`/api/admin/community/posts/${encodeURIComponent(slug)}`); openModal("게시글 관리",`<form id="post-form" class="form-grid"><label class="wide">제목<input name="title" required value="${esc(p.title)}"></label><label class="wide">내용<textarea name="content" required>${esc(p.content)}</textarea></label><label>노출 상태<select name="hidden"><option value="false" ${!p.is_hidden?"selected":""}>공개</option><option value="true" ${p.is_hidden?"selected":""}>숨김</option></select></label><div class="wide modal-actions"><button type="button" class="secondary" onclick="closeModal()">취소</button><button>저장</button></div></form>`); $("#post-form").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);await request(`/api/admin/community/posts/${encodeURIComponent(slug)}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({title:f.get("title"),content:f.get("content"),is_hidden:f.get("hidden")==="true"})});closeModal();flash("게시글을 수정했습니다.");community();}; }
async function reports() { const rows=await request("/api/admin/comment-reports?limit=100"); openModal("댓글 신고 목록",`<div class="table-wrap"><table class="table"><thead><tr><th>번호</th><th>내용</th><th>상태</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.id}</td><td class="wrap">${esc(r.content_snapshot)}</td><td><span class="badge ${r.status==="pending"?"warn":""}">${esc(r.status)}</span></td><td><button data-report="${r.id}">상세</button></td></tr>`).join("")}</tbody></table></div>`); $("#modal-content").querySelectorAll("[data-report]").forEach(b=>b.onclick=()=>reportDetail(b.dataset.report)); }
async function reportDetail(id) { const r=await request(`/api/admin/comment-reports/${id}`); openModal(`신고 #${r.id}`,`<p class="result">${esc(r.content_snapshot)}</p><p class="small">신고자 #${r.reporter_id ?? "삭제됨"} · 대상 #${r.reported_user_id ?? "삭제됨"}</p><form id="report-form" class="form-grid"><label>처리 상태<select name="status"><option value="reviewing">검토 중</option><option value="resolved">처리 완료</option><option value="dismissed">기각</option></select></label><label>댓글 모더레이션<select name="moderation"><option value="">변경 안 함</option><option value="hide">숨김</option><option value="restore">복원</option></select></label><label class="wide">처리 메모<textarea name="note" required>${esc(r.resolution_note || "")}</textarea></label><div class="wide modal-actions"><button type="button" class="secondary" onclick="closeModal()">취소</button><button>처리 저장</button></div></form>`); $("#report-form").onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),status=f.get("status"),note=f.get("note").trim();await request(`/api/admin/comment-reports/${id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({status,resolution_note:note})});if(f.get("moderation")&&r.post_id&&r.comment_id)await request(`/api/admin/community/comments/${r.post_id}/${r.comment_id}/moderation`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:f.get("moderation"),reason:note||null})});closeModal();flash("신고 처리를 저장했습니다.");}; }
async function blocks() { const rows=await request("/api/admin/user-blocks?limit=100"); openModal("사용자 차단 현황",rows.length?`<div class="table-wrap"><table class="table"><thead><tr><th>차단한 사용자</th><th>차단된 사용자</th><th>일시</th></tr></thead><tbody>${rows.map(b=>`<tr><td>#${b.blocker_id}</td><td>#${b.blocked_user_id}</td><td>${date(b.created_at)}</td></tr>`).join("")}</tbody></table></div>`:`<p class="muted">차단 내역이 없습니다.</p>`); }

async function data() {
  $("#content").innerHTML = `<div class="grid split"><section class="card"><h3>크롤링 실행</h3><p class="muted">실행 결과는 아래에 표시됩니다. 기록·실패 로그 API는 확장용으로만 서버에 연결됩니다.</p><div class="actions"><button data-crawl="/api/shuttles/crawl">셔틀 시간표 수집</button><button data-crawl="/api/daily-menus/crawl">학식 메뉴 수집</button><button data-crawl="/api/notices/crawl">학교 공지 수집</button></div><div id="crawl-result"></div></section><section class="card"><h3>강의 HTML 등록</h3><p class="muted">수강신청 시스템에서 저장한 HTML 파일을 선택해 등록합니다.</p><input id="course-file" type="file" accept=".html,text/html"><label class="small">학과(선택)<input id="course-dept" placeholder="예: 소프트웨어전공"></label><p><button id="course-upload">HTML 등록</button></p><div id="course-result"></div></section></div><section class="card" style="margin-top:16px"><h3>학과별 강의 크롤링</h3><p class="muted">수강신청 세션 정보가 필요한 관리자 작업입니다. 서버 요청 형식(JSON)을 입력해 실행합니다.</p><textarea id="crawl-json" style="width:100%;min-height:130px;border:1px solid #d6e1df;border-radius:8px;padding:11px" placeholder='{"session_cookie":"…","year":"2026","semester":"2","student_number":"…","student_department_code":"…","fact_code":"…","fact_srch":"…","departments":[{"code":"…","name":"…"}]}'></textarea><p><button id="course-crawl">학과별 강의 크롤링 실행</button></p><div id="department-result"></div></section>`;
  $("#content").querySelectorAll("[data-crawl]").forEach(b => b.onclick = async () => { b.disabled=true; try { const r=await request(b.dataset.crawl,{method:"POST"}); $("#crawl-result").innerHTML=`<p class="result">${esc(r.message || "완료")} ${r.count != null ? `(${r.count}건)` : ""}</p>`; flash("크롤링 작업을 완료했습니다."); } catch(e) { $("#crawl-result").innerHTML=`<p class="error">${esc(e.message)}</p>`; } finally { b.disabled=false; } });
  $("#course-upload").onclick = async () => { const file=$("#course-file").files[0]; if(!file) return flash("HTML 파일을 선택해 주세요.",true); const form=new FormData();form.append("file",file);form.append("department",$("#course-dept").value.trim());form.append("save","true");try{const r=await request("/api/courses/import-html-file",{method:"POST",body:form});$("#course-result").innerHTML=`<p class="result">분석 ${r.parsed_count}건 · 등록 ${r.saved_count}건</p>`;}catch(e){$("#course-result").innerHTML=`<p class="error">${esc(e.message)}</p>`;}};
  $("#course-crawl").onclick=async()=>{try{const body=JSON.parse($("#crawl-json").value);const r=await request("/api/courses/crawl-departments",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});$("#department-result").innerHTML=`<p class="result">학과 ${r.department_count}개 · 분석 ${r.parsed_count}건 · 등록 ${r.saved_count}건</p>`;}catch(e){$("#department-result").innerHTML=`<p class="error">${esc(e.message || "JSON 형식을 확인해 주세요.")}</p>`;}};
}

async function users() {
  const load = async () =>{
    const q=$("#user-query").value.trim(),
    active=$("#active-filter").value,
    admin=$("#admin-filter").value;
    const params=new URLSearchParams({limit:"100"});
    if(q)params.set("keyword",q);
    if(active)params.set("is_active",active);
    if(admin)params.set("is_admin",admin);
    const rows=await request(`/api/admin/users?${params}`);
    $("#user-rows").innerHTML=rows.length?rows.map(u=>
      `<tr>
        <td>
          <b>${esc(u.name)}</b>
          <br><span class="small">#${u.id}</span></td><td>${esc(u.email)}<br><span class="small">${esc(u.department || "학과 미입력")} · ${esc(u.student_id || "-")}</span></td><td>${u.is_active?'<span class="badge">활성</span>':'<span class="badge off">비활성</span>'}</td><td>${u.is_admin?'<span class="badge">관리자</span>':'-'}</td><td class="actions"><button data-detail="${u.id}">상세</button><button data-active="${u.id}" data-value="${!u.is_active}">${u.is_active?"비활성화":"활성화"}</button><button class="secondary" data-role="${u.id}" data-value="${!u.is_admin}" ${!u.is_active?"disabled":""}>${u.is_admin?"권한 해제":"관리자 지정"}</button></td></tr>`).join(""):`<tr><td colspan="5" class="empty">회원이 없습니다.</td></tr>`;$("#user-rows").onclick=async e=>{const b=e.target.closest("button");if(!b)return;try{if(b.dataset.detail)return userDetail(b.dataset.detail);if(b.dataset.active){await request(`/api/admin/users/${b.dataset.active}/active`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({is_active:b.dataset.value==="true"})});flash("계정 상태를 변경했습니다.");}if(b.dataset.role){await request(`/api/admin/users/${b.dataset.role}/role`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({is_admin:b.dataset.value==="true"})});flash("관리자 권한을 변경했습니다.");}load();}catch(err){flash(err.message,true);}};};
  $("#content").innerHTML=`<div class="toolbar"><input id="user-query" placeholder="이름, 이메일, 학번 검색"><select id="active-filter"><option value="">계정 상태 전체</option><option value="true">활성</option><option value="false">비활성</option></select><select id="admin-filter"><option value="">권한 전체</option><option value="true">관리자</option><option value="false">일반 회원</option></select><button id="user-search" class="secondary">검색</button><button id="user-blocks">차단 현황</button></div><div class="card table-wrap"><table class="table"><thead><tr><th>회원</th><th>연락처·정보</th><th>상태</th><th>권한</th><th></th></tr></thead><tbody id="user-rows"></tbody></table></div>`;$("#user-search").onclick=load;$("#user-blocks").onclick=blocks;load();
}
async function userDetail(id){const u=await request(`/api/admin/users/${id}`);openModal("회원 상세",`<div class="result"><b>${esc(u.name)} (#${u.id})</b><br>이메일: ${esc(u.email)}<br>학번: ${esc(u.student_id || "-")}<br>학과/학년: ${esc(u.department || "-")} / ${esc(u.grade || "-")}<br>가입일: ${date(u.created_at)}<br>계정: ${u.is_active?"활성":"비활성"} · ${u.is_admin?"관리자":"일반 회원"}</div><div class="modal-actions"><button class="secondary" onclick="closeModal()">닫기</button></div>`);}

async function start() {
  if (!state.token) return showLogin();
  try { state.user=await request("/auth/me"); if(!state.user.is_admin) throw new Error("관리자 권한이 없는 계정입니다."); showApp(); } catch(e) { sessionStorage.removeItem("knu_admin_token"); state.token=null; showLogin(e.message); }
}
function showLogin(message = "") { $("#app-view").hidden=true; $("#login-view").hidden=false; $("#login-error").textContent=message; if (window.location.pathname !== "/login") window.history.replaceState({}, "", "/login"); }
function showApp(){ $("#login-view").hidden=true;$("#app-view").hidden=false;$("#admin-name").textContent=`${state.user.name} 관리자`; const requested = viewFromPath(); goTo(requested, window.location.pathname === "/" || window.location.pathname === "/login"); }
$("#login-form").onsubmit=async e=>{e.preventDefault();const error=$("#login-error"),submit=e.currentTarget.querySelector("button[type=submit], button:not([type])"),original=submit.textContent;error.textContent="";submit.disabled=true;submit.textContent="로그인 확인 중…";try{const r=await request("/auth/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:$("#email").value.trim(),password:$("#password").value})});state.token=r.access_token;sessionStorage.setItem("knu_admin_token",state.token);state.user=await request("/auth/me");if(!state.user.is_admin)throw new Error("관리자 권한이 없는 계정입니다.");showApp();}catch(err){sessionStorage.removeItem("knu_admin_token");state.token=null;error.textContent=err.message;}finally{submit.disabled=false;submit.textContent=original;}};
$("#logout").onclick=()=>{sessionStorage.removeItem("knu_admin_token");state.token=null;state.user=null;showLogin();};
window.addEventListener("popstate", () => { if (!state.token) return showLogin(); goTo(viewFromPath(), true); });
start();

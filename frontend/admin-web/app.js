const API = (window.ADMIN_API_URL || "").replace(/\/+$/, "");
const state = { token: sessionStorage.getItem("knu_admin_token"), user: null, view: document.body.dataset.page || "dashboard", noticeSort: "id_desc" };
const $ = (s) => document.querySelector(s);
const esc = (v = "") => String(v).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const date = (v) => v ? new Date(v).toLocaleString("ko-KR") : "-";

async function request(path, options = {}) {
  if (!API) throw new Error("관리자 API 주소가 설정되지 않았습니다.");
  const { timeoutMs = 15000, ...fetchOptions } = options;
  const headers = { Accept: "application/json", ...(fetchOptions.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let r;
  try {
    r = await fetch(`${API}${path}`, { ...fetchOptions, headers, signal: controller.signal });
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
function flash(message, error = false) {

  const node = $("#flash"); 
  
  node.className = `flash${error ? " error" : ""}`; 
  node.textContent = message; 
  setTimeout(() => { if (node.textContent === message) node.textContent = ""; }, 4500); 
}
function button(label, attrs = "") { return `<button ${attrs}>${label}</button>`; }
function openModal(title, body) {
   $("#modal-content").innerHTML = 
     `<div class="modal-body">
        <div class="modal-head">
          <h2>${title}</h2>
          <button class="secondary" onclick="closeModal()">닫기</button>
        </div>${body}
      </div>`; 
    $("#modal").showModal(); 
}
function closeModal() { $("#modal").close(); }
window.closeModal = closeModal;

const menus = [
  ["dashboard", "▦", "대시보드"], 
  ["notices", "▣", "공지사항"], 
  ["community", "⚑", "커뮤니티"], 
  ["data", "↻", "서비스 데이터"], 
  ["users", "♙", "회원 관리"]
];
const paths = { dashboard: "/dashboard.html", notices: "/notices.html", community: "/community.html", data: "/data.html", users: "/users.html" };
function navigate(view) { window.location.assign(paths[view] || paths.dashboard); }
function renderNav() { $("#nav").innerHTML = menus.map(([key, icon, label]) => `<a class="${key === state.view ? "active" : ""}" href="${paths[key]}"><span>${icon}</span>${label}</a>`).join(""); }
async function renderView(view) { 
  state.view = view; 
  renderNav(); 
  const label = menus.find(x => x[0] === view)[2]; 
  $("#page-title").textContent = label; 
  $("#content").innerHTML = `<div class="empty">불러오는 중…</div>`;
  try {
    await ({ dashboard, notices, community, data, users }[view])(); 
  } catch (e) { $("#content").innerHTML = `<div class="card empty">${esc(e.message)}</div>`; } 
}

async function dashboard() {
  const [d, recentBlocks] = await Promise.all([
    request("/api/admin/dashboard"),
    request("/api/admin/user-blocks?limit=5"),
  ]);
  const statusLabel = { pending: "대기 중", reviewing: "검토 중", resolved: "처리 완료", dismissed: "기각" };
  $("#content").innerHTML = 
  `<div class="grid stats">${[["전체 회원",d.total_users],["활성 회원",d.active_users],["게시글",d.total_posts],["미처리 신고",d.pending_reports]].map(([l,n])=>
    `<div class="card stat">
      <div class="label">${l}</div>
      <div class="number">${n}</div>
    </div>`).join("")}
  </div>
  <section class="card" style="margin-top:16px">
      <h3>주요 관리 메뉴</h3>
      <div class="quick">
        <button data-go="notices">공지사항 관리<br><small>등록·수정·크롤링</small></button>
        <button data-go="community">커뮤니티 관리<br><small>게시글·신고 모더레이션</small></button>
        <button data-go="data">서비스 데이터<br><small>크롤링·강의 등록</small></button>
        <button data-go="users">회원 관리<br><small>권한·계정 상태</small></button>
      </div>
  </section>
  <div class="grid split" style="margin-top:16px">
    <section class="card">
      <div class="section-heading">
        <h3>최근 신고</h3>
        <span class="badge warn">${d.pending_reports}건 미처리</span>
      </div>
      ${d.recent_reports.length ?
        d.recent_reports.map(r=>`<button class="dashboard-item" data-report-detail="${r.id}">
          <span class="dashboard-item-main"><b>#${r.id} · ${esc(r.content_snapshot).slice(0,90)}</b><span class="small">${esc(r.reason)} · ${date(r.created_at)}</span></span>
          <span class="badge ${r.status === "pending" || r.status === "reviewing" ? "warn" : ""}">${statusLabel[r.status] || esc(r.status)}</span>
        </button>`).join("")
        :
        `<p class="muted">최근 신고가 없습니다.</p>`}
    </section>
    <section class="card">
      <div class="section-heading">
        <h3>최근 차단</h3>
        <span class="badge off">${recentBlocks.length}건</span>
      </div>
      ${recentBlocks.length ?
        recentBlocks.map(b=>`<button class="dashboard-item" data-block-detail="${b.id}">
          <span class="dashboard-item-main"><b>#${b.blocker_id} → #${b.blocked_user_id}</b><span class="small">사용자 차단 · ${date(b.created_at)}</span></span>
          <span class="badge off">차단됨</span>
        </button>`).join("")
        :
        `<p class="muted">최근 차단 내역이 없습니다.</p>`}
    </section>
  </div>`;
  $("#content").querySelectorAll("[data-go]").forEach(b => b.onclick = () => navigate(b.dataset.go));
  $("#content").querySelectorAll("[data-report-detail]").forEach(b => b.onclick = () => reportDetail(b.dataset.reportDetail));
  $("#content").querySelectorAll("[data-block-detail]").forEach(b => b.onclick = () => blockDetail(b.dataset.blockDetail, recentBlocks));
}

async function notices() {
  const load = async () => { 
    const keyword = $("#notice-query").value.trim(); 
    const rows = await request(`/api/notices/${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`); 
    const sort = $("#notice-sort").value;
    const publishedAt = n => Date.parse(n.published_at || n.crawled_at || "") || 0;
    rows.sort((a, b) => {
      if (sort === "id_asc") return a.id - b.id;
      if (sort === "published_desc") return publishedAt(b) - publishedAt(a) || b.id - a.id;
      if (sort === "published_asc") return publishedAt(a) - publishedAt(b) || a.id - b.id;
      if (sort === "important") return Number(b.is_important) - Number(a.is_important) || publishedAt(b) - publishedAt(a) || b.id - a.id;
      return b.id - a.id;
    });
    
    $("#notice-rows").innerHTML = 
      rows.length ? rows.map(n=>
          `<tr>
            <td>${n.id}</td>
            <td class="wrap"><b>${esc(n.title)}</b><br>
              <span class="small">${esc(n.category)}</span>
            </td>
            <td>${n.is_important ? `<span class="badge">중요</span>` : "-"}</td>
            <td>${date(n.published_at || n.crawled_at)}</td>
            <td class="actions">
              <button data-edit="${n.id}">수정</button>
              <button class="danger" data-delete="${n.id}">삭제</button>
            </td>
          </tr>`).join("") 
            : 
          `<tr>
            <td colspan="5" class="empty">공지사항이 없습니다.</td>
          </tr>`;
    $("#notice-rows").onclick = async e => {
        const id = e.target.dataset.edit || e.target.dataset.delete; 
       
        if (!id) return;
        if (e.target.dataset.delete) {
            if (confirm("이 공지를 삭제할까요?")) { 
              try {
                await request(`/api/notices/${id}`, {method:"DELETE"});
                flash("공지를 삭제했습니다.");
                await load();
              } catch (error) {
                flash(`공지 삭제에 실패했습니다: ${error.message}`, true);
              }
            } return; 
        } 
        const n = rows.find(x=>x.id === Number(id)); noticeForm(n); 
    }; 
  };
  $("#content").innerHTML = 
    `<div class="toolbar">
      <input id="notice-query" placeholder="제목 또는 내용 검색">
      <button id="notice-search" class="secondary">검색</button>
      <label class="sort-control">정렬
        <select id="notice-sort" aria-label="공지사항 정렬 방식">
          <option value="id_desc">ID 높은 순</option>
          <option value="id_asc">ID 낮은 순</option>
          <option value="published_desc">게시일 최신순</option>
          <option value="published_asc">게시일 오래된 순</option>
          <option value="important">중요 공지 우선</option>
        </select>
      </label>
      <button id="notice-new">공지 등록</button>
      <button id="notice-crawl" class="secondary">학교 공지 수집 시작</button>
    </div>
    <div class="card table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th><th>제목</th>
            <th>상태</th>
            <th>게시일</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="notice-rows"></tbody>
      </table>
    </div>`;
  $("#notice-sort").value = state.noticeSort;
  $("#notice-sort").onchange = () => { state.noticeSort = $("#notice-sort").value; load(); };
  $("#notice-search").onclick = load; 
  $("#notice-new").onclick = () => noticeForm(); 
  $("#notice-crawl").onclick = async () => { 
    $("#notice-crawl").disabled=true; 
    try {
      const r=await request("/api/notices/crawl",{method:"POST",timeoutMs:30000});
      flash(r.message || "공지사항 크롤러 작업을 시작했습니다.");
    } catch (e) {
      flash(e.message, true);
    } finally {
        $("#notice-crawl").disabled=false; 
    } 
  }; load();
}

function noticeForm(n = null) {
  openModal(n ? "공지 수정" : "공지 등록", 
    `<form id="notice-form" class="form-grid">
      <label class="wide">제목<input name="title" required value="${esc(n?.title)}"></label>
      <label>분류<input name="category" required value="${esc(n?.category || "학사")}"></label>
      <label>중요 공지
        <select name="important">
          <option value="false">일반</option>
          <option value="true" ${n?.is_important ? "selected" : ""}>중요</option>
        </select>
      </label>
      <label class="wide">내용
        <textarea name="content" required>${esc(n?.content || "")}</textarea>
      </label><div class="wide modal-actions">
      <button type="button" class="secondary" onclick="closeModal()">취소</button>
      <button>저장</button>
    </div>
    </form>`); 
    
    $("#notice-form").onsubmit = async e => { 
      e.preventDefault(); 
      
      const f = new FormData(e.target), 
      body={
        title:f.get("title").trim(),
        category:f.get("category").trim(),content:f.get("content").trim(),is_important:f.get("important")==="true"
      }; 
      
      await request(
        n?
          `/api/notices/${n.id}`
        :
          "/api/notices/"
        
        ,{method:n?"PUT":"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}
      );
      
      closeModal(); 
      flash("공지를 저장했습니다."); 
      notices(); 
    }; 
  }

async function community() {
  let blockRows = [];
  $("#content").innerHTML =
    `<div class="grid split moderation-columns">
      <section class="card table-wrap">
        <div class="section-heading">
          <div>
            <h3>댓글 신고 목록</h3>
            <p class="muted">신고 내용을 확인하고 처리 상태를 변경합니다.</p>
          </div>
          <button id="refresh-reports" class="secondary">새로고침</button>
        </div>
        <table class="table">
          <thead><tr><th>번호</th><th>신고 내용</th><th>상태</th><th>접수일</th></tr></thead>
          <tbody id="community-report-rows"><tr><td colspan="4" class="empty">불러오는 중…</td></tr></tbody>
        </table>
      </section>
      <section class="card table-wrap">
        <div class="section-heading">
          <div>
            <h3>사용자 차단 현황</h3>
            <p class="muted">차단한 사용자와 차단된 사용자를 확인합니다.</p>
          </div>
          <button id="refresh-blocks" class="secondary">새로고침</button>
        </div>
        <table class="table">
          <thead><tr><th>차단한 사용자</th><th>차단된 사용자</th><th>차단일</th></tr></thead>
          <tbody id="community-block-rows"><tr><td colspan="3" class="empty">불러오는 중…</td></tr></tbody>
        </table>
      </section>
    </div>`;

  const loadReports = async () => {
    const rows = await request("/api/admin/comment-reports?limit=100");
    $("#community-report-rows").innerHTML = rows.length ? rows.map(r =>
      `<tr class="clickable-row" data-report-detail="${r.id}">
        <td>#${r.id}</td>
        <td class="wrap">${esc(r.content_snapshot)}</td>
        <td><span class="badge ${r.status === "pending" || r.status === "reviewing" ? "warn" : ""}">${esc({pending:"대기 중",reviewing:"검토 중",resolved:"처리 완료",dismissed:"기각"}[r.status] || r.status)}</span></td>
        <td>${date(r.created_at)}</td>
      </tr>`).join("") : `<tr><td colspan="4" class="empty">신고 내역이 없습니다.</td></tr>`;
    $("#community-report-rows").onclick = e => {
      const row = e.target.closest("[data-report-detail]");
      if (row) reportDetail(row.dataset.reportDetail);
    };
  };
  const loadBlocks = async () => {
    blockRows = await request("/api/admin/user-blocks?limit=100");
    $("#community-block-rows").innerHTML = blockRows.length ? blockRows.map(b =>
      `<tr class="clickable-row" data-block-detail="${b.id}">
        <td>#${b.blocker_id}</td>
        <td>#${b.blocked_user_id}</td>
        <td>${date(b.created_at)}</td>
      </tr>`).join("") : `<tr><td colspan="3" class="empty">차단 내역이 없습니다.</td></tr>`;
    $("#community-block-rows").onclick = e => {
      const row = e.target.closest("[data-block-detail]");
      if (row) blockDetail(row.dataset.blockDetail, blockRows);
    };
  };
  $("#refresh-reports").onclick = () => loadReports().catch(e => flash(e.message, true));
  $("#refresh-blocks").onclick = () => loadBlocks().catch(e => flash(e.message, true));
  await Promise.all([loadReports(), loadBlocks()]);
}

async function postDetail(slug) { 
  const p=await request(`/api/admin/community/posts/${encodeURIComponent(slug)}`); 
  
  openModal("게시글 관리",
    `<form id="post-form" class="form-grid">
      <label class="wide">제목
      <input name="title" required value="${esc(p.title)}"></label>
      <label class="wide">내용
        <textarea name="content" required>${esc(p.content)}</textarea>
      </label>
      <label>노출 상태
        <select name="hidden">
          <option value="false" ${!p.is_hidden?"selected":""}>공개</option>
          <option value="true" ${p.is_hidden?"selected":""}>숨김</option>
        </select>
      </label>
      <div class="wide modal-actions">
        <button type="button" class="secondary" onclick="closeModal()">취소</button>
        <button>저장</button>
      </div>
    </form>`
  ); 
    
  $("#post-form").onsubmit=async e=>{
    e.preventDefault();
    
    const f=new FormData(e.target);
    
    await request(
      `/api/admin/community/posts/${encodeURIComponent(slug)}`,
      {
        method:"PATCH",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          title:f.get("title"),
          content:f.get("content"),
          is_hidden:f.get("hidden")==="true"
        })
      }
    );
    closeModal();
    flash("게시글을 수정했습니다.");
    community();
  };
}

async function reports() { 
  const rows=await request("/api/admin/comment-reports?limit=100"); 
  openModal("댓글 신고 목록",
    `<div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>번호</th>
            <th>내용</th>
            <th>상태</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${rows.map(r=>
          `<tr>
            <td>${r.id}</td>
            <td class="wrap">${esc(r.content_snapshot)}</td>
            <td><span class="badge ${r.status==="pending"?"warn":""}">${esc(r.status)}</span></td>
            <td><button data-report="${r.id}">상세</button></td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`); 
    
    $("#modal-content").querySelectorAll("[data-report]").forEach(b=>b.onclick=()=>reportDetail(b.dataset.report)
  ); 
}

async function reportDetail(id) { 
  const r=await request(`/api/admin/comment-reports/${id}`); 
  const statusLabel = { pending: "대기 중", reviewing: "검토 중", resolved: "처리 완료", dismissed: "기각" };
  
  openModal(`신고 #${r.id}`,
   `<div class="result"><b>신고 상태: ${statusLabel[r.status] || esc(r.status)}</b><br>${esc(r.content_snapshot)}</div>
    <p class="small">신고자 #${r.reporter_id ?? "삭제됨"} · 대상 #${r.reported_user_id ?? "삭제됨"}</p>
    <form id="report-form" class="form-grid">
      <label>처리 상태
        <select name="status">
          <option value="reviewing" ${r.status === "reviewing" ? "selected" : ""}>검토 중</option>
          <option value="resolved" ${r.status === "resolved" ? "selected" : ""}>처리 완료</option>
          <option value="dismissed" ${r.status === "dismissed" ? "selected" : ""}>기각</option>
        </select>
      </label>
      <label>댓글 모더레이션
        <select name="moderation">
          <option value="">변경 안 함</option>
          <option value="hide">숨김</option>
          <option value="restore">복원</option>
        </select></label>
      <label class="wide">처리 메모
        <textarea name="note" required>${esc(r.resolution_note || "")}</textarea>
      </label>
      <div class="wide modal-actions">
        <button type="button" class="secondary" onclick="closeModal()">취소</button>
        <button>처리 저장</button>
      </div>
    </form>`); 
    
  $("#report-form").onsubmit=async e=>{
    e.preventDefault();
    
    const f=new FormData(e.target),
    
    status=f.get("status"),
    note=f.get("note").trim();
    
    await request(`/api/admin/comment-reports/${id}`,
      {
        method:"PATCH",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({status,resolution_note:note})
      }
    );
      
    if(f.get("moderation")&&r.post_id&&r.comment_id)
      await request(`/api/admin/community/comments/${r.post_id}/${r.comment_id}/moderation`,
        {
          method:"PATCH",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({action:f.get("moderation"),reason:note||null})
        }
    );
    closeModal();
    flash("신고 처리를 저장했습니다.");
  }; 
}
function blockDetail(id, rows) {
  const block = rows.find(item => String(item.id) === String(id));
  if (!block) return;
  openModal(`차단 내역 #${block.id}`,
    `<div class="result">
      <b>차단 상태: 차단됨</b>
      <br>차단한 사용자: #${block.blocker_id}
      <br>차단된 사용자: #${block.blocked_user_id}
      <br>차단 일시: ${date(block.created_at)}
    </div>
    <div class="modal-actions">
      <button class="secondary" onclick="closeModal()">닫기</button>
    </div>`
  );
}
async function blocks() { 
  const rows=await request("/api/admin/user-blocks?limit=100"); 
  
  openModal("사용자 차단 현황",
    rows.length?
      `<div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>차단한 사용자</th>
              <th>차단된 사용자</th>
              <th>일시</th>
            </tr>
          </thead>
          <tbody>${rows.map(b=>
            `<tr>
              <td>#${b.blocker_id}</td>
              <td>#${b.blocked_user_id}</td>
              <td>${date(b.created_at)}</td>
            </tr>`).join("")}
          </tbody>
        </table>
      </div>`
    :
      `<p class="muted">차단 내역이 없습니다.</p>`
  ); 
}

async function data() {
  const crawlItems = [
    ["shuttle", "셔틀 시간표 수집", "/api/shuttles/crawl"],
    ["menu", "학식 메뉴 수집", "/api/daily-menus/crawl"],
    ["notice", "학교 공지 수집", "/api/notices/crawl"],
  ];
  const crawlKey = key => `knu_admin_last_crawl_${key}`;
  const formatLastCrawl = key => {
    const value = localStorage.getItem(crawlKey(key));
    return value ? date(value) : "기록 없음";
  };
  $("#content").innerHTML =
    `<section class="card">
      <h3>크롤링 실행</h3>
      <p class="muted">필요한 데이터 수집 작업을 선택해 실행합니다.</p>
      <div class="grid crawl-cards">
        ${crawlItems.map(([key, label, endpoint]) => `<div class="crawl-card">
          <h4>${label}</h4>
          <div class="crawl-action-row">
            <button data-crawl="${endpoint}" data-crawl-key="${key}">실행</button>
            <span class="crawl-last-run">최종 실행: <b data-last-crawl="${key}">${formatLastCrawl(key)}</b></span>
          </div>
          <div class="small" data-crawl-result="${key}"></div>
        </div>`).join("")}
      </div>
    </section>`;
  $("#content").querySelectorAll("[data-crawl]").forEach(b => 
    b.onclick = async () => { 
      b.disabled=true; 
      
      try { 
        const r=await request(b.dataset.crawl,{method:"POST",timeoutMs:30000});
        const completedAt = new Date().toISOString();
        localStorage.setItem(crawlKey(b.dataset.crawlKey), completedAt);
        $(`[data-last-crawl="${b.dataset.crawlKey}"]`).textContent = date(completedAt);
        $(`[data-crawl-result="${b.dataset.crawlKey}"]`).textContent = `${r.message || "완료"}${r.count != null ? ` (${r.count}건)` : ""}`;
        flash(r.status === "started" ? "크롤링 작업을 시작했습니다." : "크롤링 작업을 완료했습니다.");
      } catch(e) { 
        $(`[data-crawl-result="${b.dataset.crawlKey}"]`).textContent = e.message;
        $(`[data-crawl-result="${b.dataset.crawlKey}"]`).className = "error";
      } finally { b.disabled=false; } 
    }
  );
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
          <b>${esc(u.name)}</b><br>
          <span class="small">#${u.id}</span>
        </td>
        <td>${esc(u.email)}<br>
          <span class="small">${esc(u.department || "학과 미입력")} · ${esc(u.student_id || "-")}</span>
        </td>
        <td>${u.is_active?'<span class="badge">활성</span>':'<span class="badge off">비활성</span>'}</td>
        <td>${u.is_admin?'<span class="badge">관리자</span>':'-'}</td>
        <td class="actions">
          <button data-active="${u.id}" data-value="${!u.is_active}">${u.is_active?"비활성화":"활성화"}</button>
          <button class="secondary" data-role="${u.id}" data-value="${!u.is_admin}" ${!u.is_active?"disabled":""}>${u.is_admin?"권한 해제":"관리자 지정"}</button>
          <button class="danger" data-delete="${u.id}" data-name="${esc(u.name)}">회원 삭제</button>
        </td>
      </tr>`).join("")
      :
      `<tr>
        <td colspan="5" class="empty">회원이 없습니다.</td>
      </tr>`;
      
    $("#user-rows").onclick=async e=>{
      const b=e.target.closest("button");
      if(!b) {
        const row=e.target.closest("tr[data-user]");
        if (row) return userDetail(row.dataset.user);
        return;
      }
      
      try{
        if(b.dataset.delete)
          return confirmUserDelete(b.dataset.delete, b.dataset.name, load);
        if(b.dataset.active) {
          await request(`/api/admin/users/${b.dataset.active}/active`,
            {
              method:"PATCH",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({is_active:b.dataset.value==="true"})
            }
          );
          flash("계정 상태를 변경했습니다.");
        }
        if(b.dataset.role) {
          await request(`/api/admin/users/${b.dataset.role}/role`,
            {
              method:"PATCH",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({is_admin:b.dataset.value==="true"})
            }
          );
          flash("관리자 권한을 변경했습니다.");
        }
        load();
      } catch(err) {flash(err.message,true);}
    };
  };
  $("#content").innerHTML=
    `<div class="toolbar">
      <input id="user-query" placeholder="이름, 이메일, 학번 검색">
      <select id="active-filter">
        <option value="">계정 상태 전체</option>
        <option value="true">활성</option>
        <option value="false">비활성</option>
      </select>
      <select id="admin-filter">
        <option value="">권한 전체</option>
        <option value="true">관리자</option>
        <option value="false">일반 회원</option>
      </select>
      <button id="user-search" class="secondary">검색</button>
      <button id="user-blocks">차단 현황</button>
    </div>
    <div class="card table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>회원</th>
            <th>연락처·정보</th>
            <th>상태</th>
            <th>권한</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="user-rows"></tbody>
      </table>
    </div>`;
    $("#user-search").onclick=load;
    $("#user-blocks").onclick=blocks;
    load();
}
async function userDetail(id) {
  const u=await request(`/api/admin/users/${id}`);
  openModal("회원 상세",
    `<div class="result">
      <b>${esc(u.name)} (#${u.id})</b>
      <br>이메일: ${esc(u.email)}
      <br>학번: ${esc(u.student_id || "-")}
      <br>학과/학년: ${esc(u.department || "-")} / ${esc(u.grade || "-")}
      <br>가입일: ${date(u.created_at)}
      <br>계정: ${u.is_active?"활성":"비활성"} · ${u.is_admin?"관리자":"일반 회원"}
    </div>
    <div class="modal-actions">
      <button class="secondary" onclick="closeModal()">닫기</button>
    </div>`
  );
}

function confirmUserDelete(id, name, refresh) {
  openModal("회원 삭제", `
    <p class="muted"><b>${esc(name)}</b> 회원의 계정과 연결된 서비스 데이터가 영구 삭제됩니다.</p>
    <p class="error">정말 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.</p>
    <div class="modal-actions">
      <button class="secondary" type="button" onclick="closeModal()">취소</button>
      <button id="confirm-user-delete" class="danger" type="button">회원 삭제</button>
    </div>
  `);
  $("#confirm-user-delete").onclick = async () => {
    const button = $("#confirm-user-delete");
    button.disabled = true;
    button.textContent = "삭제 중…";
    try {
      await request(`/api/admin/users/${id}`, { method: "DELETE" });
      closeModal();
      flash("회원 계정을 영구 삭제했습니다.");
      await refresh();
    } catch (error) {
      button.disabled = false;
      button.textContent = "회원 삭제";
      flash(error.message, true);
    }
  };
}

async function start() {
  const isLogin = document.body.dataset.page === "login";
  if (!state.token) { if (!isLogin) window.location.replace("/login.html"); return; }
  try {
    state.user=await request("/auth/me");
    if(!state.user.is_admin) throw new Error("관리자 권한이 없는 계정입니다.");
    if (isLogin) return window.location.replace("/dashboard.html");
    showApp();
  } catch(e) {
    sessionStorage.removeItem("knu_admin_token"); state.token=null;
    if (!isLogin) return window.location.replace("/login.html");
    $("#login-error").textContent=e.message;
  }
}
function showApp() { 
  $("#admin-name").textContent=`${state.user.name} 관리자`; 
  renderNav(); 
  renderView(state.view); 
}
if ($("#login-form")) 
  $("#login-form").onsubmit=async e => {
  e.preventDefault();
  
  const error=$("#login-error"), 
  submit=e.currentTarget.querySelector("button[type=submit], button:not([type])"),
  original=submit.textContent;
  error.textContent="";
  submit.disabled=true;
  submit.textContent="로그인 확인 중…";
  
  try{
    const r=await request("/auth/login",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({email:$("#email").value.trim(),password:$("#password").value})
      }
    );
    state.token=r.access_token;sessionStorage.setItem("knu_admin_token",state.token);
    state.user=await request("/auth/me");
    
    if(!state.user.is_admin)
      throw new Error("관리자 권한이 없는 계정입니다.");
    
    window.location.replace("/dashboard.html");
  } catch(err) {
    sessionStorage.removeItem("knu_admin_token");
    state.token=null;
    error.textContent=err.message;
  } finally {
    submit.disabled=false;
    submit.textContent=original;
  }
};

if ($("#logout")) $("#logout").onclick=()=>{sessionStorage.removeItem("knu_admin_token");window.location.replace("/login.html");};
start();

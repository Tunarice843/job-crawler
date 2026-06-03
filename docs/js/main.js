// =============================================================
// 채용공고 대시보드
// - 데이터 소스: data/jobs.json (크롤러가 생성, GitHub Actions가 매일 갱신)
// - 확인완료 / 책갈피 상태는 브라우저 localStorage에만 저장 (서버 불필요)
// =============================================================

const DATA_URL = 'data/jobs.json';
const CHECKED_KEY = 'job_checked_items';
const BOOKMARK_KEY = 'job_bookmarks';

let allJobs = [];   // jobs.json 으로부터 로드된 전체 공고 (메모리 캐시)

// ---------- localStorage 상태 ----------
function loadState(key) {
    try {
        const saved = localStorage.getItem(key);
        return saved ? JSON.parse(saved) : {};
    } catch (e) {
        return {};
    }
}

function saveState(key, id, on) {
    const state = loadState(key);
    if (on) state[id] = true; else delete state[id];
    localStorage.setItem(key, JSON.stringify(state));
}

// ---------- 표시 유틸 ----------
function getCompanyBadgeClass(company) {
    const map = { 'SK': 'sk', '삼성': 'samsung', 'LG': 'lg', '현대차': 'hyundai', '기아차': 'kia' };
    return map[company] || '';
}

function formatDate(dateString) {
    if (!dateString) return '';
    const d = new Date(dateString);
    if (isNaN(d)) return '';
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${m}-${day}`;
}

function formatDateTime(dateString) {
    if (!dateString) return '-';
    const d = new Date(dateString);
    if (isNaN(d)) return '-';
    return `${formatDate(dateString)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

// ---------- 필터 ----------
function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.trim().toLowerCase();
    const company = document.getElementById('companyFilter').value;
    const hideChecked = document.getElementById('hideCheckedToggle').checked;
    const hideExpired = document.getElementById('hideExpiredToggle').checked;

    const checkedItems = loadState(CHECKED_KEY);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    return allJobs.filter(job => {
        if (searchTerm && !job.title.toLowerCase().includes(searchTerm)) return false;
        if (company && job.company !== company) return false;

        if (hideExpired && job.end_date) {
            const end = new Date(job.end_date);
            if (!isNaN(end)) {
                end.setHours(0, 0, 0, 0);
                if (end < today) return false;
            }
        }

        if (hideChecked && checkedItems[job.id]) return false;
        return true;
    });
}

// ---------- 렌더링 ----------
function render() {
    const jobListEl = document.getElementById('jobList');
    const emptyStateEl = document.getElementById('emptyState');

    const jobs = applyFilters();
    const checkedItems = loadState(CHECKED_KEY);
    const bookmarks = loadState(BOOKMARK_KEY);

    document.getElementById('totalJobs').textContent = jobs.length;

    if (jobs.length === 0) {
        jobListEl.style.display = 'none';
        emptyStateEl.style.display = 'block';
        return;
    }

    jobListEl.style.display = 'flex';
    emptyStateEl.style.display = 'none';

    jobListEl.innerHTML = jobs.map(job => {
        const badgeClass = getCompanyBadgeClass(job.company);
        const isChecked = checkedItems[job.id] || false;
        const isBookmarked = bookmarks[job.id] || false;

        return `
            <div class="job-card ${badgeClass} ${isChecked ? 'checked' : ''}" data-id="${job.id}">
                <div class="job-card-header">
                    <div class="job-title">${escapeHtml(job.title)}</div>
                    <button class="btn-bookmark ${isBookmarked ? 'active' : ''}" onclick="toggleBookmark('${job.id}', event)" title="책갈피">
                        ${isBookmarked ? '⭐' : '☆'}
                    </button>
                </div>
                <div class="job-meta">
                    <div class="job-meta-item">
                        <span class="company-badge ${badgeClass}">${escapeHtml(job.company)}</span>
                    </div>
                    <div class="job-meta-item">📅 ${formatDate(job.posted_date)}</div>
                    ${job.end_date ? `<div class="job-meta-item">⏰ ${formatDate(job.end_date)}</div>` : ''}
                </div>
                <a href="${job.url}" target="_blank" rel="noopener" class="job-link">🔗 공고 보기 →</a>
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="check_${job.id}" ${isChecked ? 'checked' : ''}
                           onchange="toggleCheck('${job.id}', this.checked)">
                    <label for="check_${job.id}">확인 완료</label>
                </div>
            </div>
        `;
    }).join('');
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ---------- 토글 (localStorage만 갱신, 서버 없음) ----------
function toggleBookmark(jobId, event) {
    if (event) event.stopPropagation();
    const on = !loadState(BOOKMARK_KEY)[jobId];
    saveState(BOOKMARK_KEY, jobId, on);
    render();
}

function toggleCheck(jobId, isChecked) {
    saveState(CHECKED_KEY, jobId, isChecked);
    const card = document.querySelector(`[data-id="${jobId}"]`);
    if (card) card.classList.toggle('checked', isChecked);
}

// ---------- 데이터 로드 ----------
async function loadData() {
    try {
        const res = await fetch(`${DATA_URL}?t=${Date.now()}`);  // 캐시 회피
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        allJobs = (data.jobs || []).slice();
        allJobs.sort((a, b) => new Date(b.posted_date) - new Date(a.posted_date));

        document.getElementById('updatedAt').textContent = formatDateTime(data.updated_at);
        render();
    } catch (e) {
        console.error('공고 로드 실패:', e);
        document.getElementById('jobList').innerHTML =
            '<div class="empty-state"><p>공고 데이터를 불러오지 못했습니다.<br>아직 크롤링이 실행되지 않았을 수 있습니다.</p></div>';
    }
}

// ---------- 초기화 ----------
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const companyFilter = document.getElementById('companyFilter');
    const hideCheckedToggle = document.getElementById('hideCheckedToggle');
    const hideExpiredToggle = document.getElementById('hideExpiredToggle');

    // 필터 상태 복원
    if (localStorage.getItem('hideCheckedFilter') === 'true') hideCheckedToggle.checked = true;
    if (localStorage.getItem('hideExpiredFilter') === 'true') hideExpiredToggle.checked = true;

    let debounce;
    searchInput.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(render, 250);
    });
    companyFilter.addEventListener('change', render);
    hideCheckedToggle.addEventListener('change', () => {
        localStorage.setItem('hideCheckedFilter', hideCheckedToggle.checked);
        render();
    });
    hideExpiredToggle.addEventListener('change', () => {
        localStorage.setItem('hideExpiredFilter', hideExpiredToggle.checked);
        render();
    });

    loadData();
});

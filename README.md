# 채용공고 모니터링 (삼성 · SK · LG · 현대차 · 기아차 · 한화)

여러 기업 채용 페이지를 매일 자동으로 크롤링하고, **검색어에 맞는 공고만** 한곳에 모아
아이폰 등 어디서나 웹으로 볼 수 있는 도구입니다.

현재 지원 포털: **삼성, SK, LG, 현대차, 기아차, 한화** (네이버·카카오·두나무는 추후 추가 예정)

## 구조

```
공고 크롤러/
├── config.json                 # ⭐ 검색어/대상 회사 설정 (여기만 편집)
├── requirements.txt
├── crawler/                    # 파이썬 크롤러
│   ├── utils.py                # 설정 로드, 검색어 매칭, 중복제거, 저장
│   ├── crawler_sk.py           # SK (JSON API)
│   ├── crawler_samsung.py      # 삼성 (HTML 파싱)
│   ├── crawler_lg.py           # LG (JSON API, 세션 쿠키)
│   ├── crawler_hyundai.py      # 현대차 (JSON API)
│   ├── crawler_kia.py          # 기아차 (JSON API)
│   ├── crawler_hanwha.py       # 한화 (JSON API, rcRecruit/search-rcrt)
│   └── run.py                  # 실행 진입점
├── docs/                       # 대시보드 (GitHub Pages가 이 폴더를 서빙)
│   ├── index.html
│   ├── css/style.css
│   ├── js/main.js
│   └── data/jobs.json          # 크롤러가 생성하는 결과 데이터
└── .github/workflows/crawl.yml # 매일 자동 크롤링
```

## 1. 검색어 설정 (config.json)

코드를 건드리지 않고 이 파일만 수정하면 됩니다.

```json
{
  "keywords": ["데이터", "AI", "기획"],   // 수집할 검색어. []로 비우면 전체 수집
  "keyword_match": "any",                 // "any"=하나라도 포함 / "all"=모두 포함
  "case_sensitive": false,                // 대소문자 구분 여부
  "companies": {                          // 끌 회사는 false
    "samsung": true, "sk": true,
    "lg": true, "hyundai": true, "kia": true
  },
  "max_pages": 5,                         // 회사별 최대 크롤링 페이지 수
  "output_path": "docs/data/jobs.json"    // 결과 저장 위치 (변경 불필요)
}
```

> 검색어는 **크롤링 시점**에 제목에 적용됩니다. 매칭되는 공고만 저장되므로
> 데이터가 가볍게 유지되고 대시보드가 빠릅니다.

## 2. 로컬에서 실행 / 미리보기

```bash
pip install -r requirements.txt

# 크롤링 (docs/data/jobs.json 생성·갱신)
python -m crawler.run

# 대시보드 미리보기 → 브라우저에서 http://127.0.0.1:8000
cd docs
python -m http.server 8000
```

## 3. 클라우드 자동실행 + 아이폰에서 보기 (무료)

GitHub만 있으면 **비용 없이** 매일 자동 크롤링 + 아이폰 조회가 됩니다.

1. **GitHub에 저장소 생성 후 이 폴더를 push**
2. **Actions 활성화**: 저장소 `Actions` 탭에서 워크플로 사용 허용
   - 매일 오전 9시(KST) 자동 실행, `Run workflow` 버튼으로 수동 실행도 가능
   - 실행되면 `docs/data/jobs.json`이 자동 갱신·커밋됩니다
3. **GitHub Pages 활성화**: `Settings → Pages`
   - Source: `Deploy from a branch`
   - Branch: `main` / 폴더: `/docs` 선택 후 저장
4. 잠시 후 발급되는 주소(`https://<사용자명>.github.io/<저장소명>/`)를
   **아이폰 사파리 즐겨찾기 또는 홈 화면에 추가**하면 끝.

> 확인완료·책갈피 상태는 보는 기기(브라우저)에 저장됩니다.

## 4. 새 포털 추가 방법 (네이버·카카오·두나무)

1. `crawler/crawler_<회사>.py` 생성 — 기존 `crawler_sk.py`(API) 또는
   `crawler_samsung.py`(HTML)를 복사해 응답 구조에 맞게 수정
   - 표준 반환 형식: `{id, company, title, url, posted_date, end_date}`
   - `id`는 `make_job_id(회사, 제목)`로 생성, 제목은 `matches_keywords`로 필터
2. `crawler/run.py`의 `CRAWLERS` 딕셔너리에 한 줄 등록
3. `config.json`의 `companies`에 회사 키 추가
4. `docs/index.html`의 회사 필터 `<option>`과 `docs/js/main.js`의
   `getCompanyBadgeClass` 매핑에 회사 추가 (배지 색은 `style.css`에 정의)

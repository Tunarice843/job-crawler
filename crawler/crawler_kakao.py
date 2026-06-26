#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카카오 채용공고 크롤러 (JSON API 직접 호출)
- 목록 페이지가 SPA(React)라 HTML 파싱 불가 → 공개 API 사용
- 목록 API: https://careers.kakao.com/public/api/job-list
  (공개 엔드포인트, GET. part(직군)별로 조회해야 하며, 비우면 TECHNOLOGY가 기본)
- 재무/회계 공고는 주로 STAFF·BUSINESS_SERVICES 직군에 있어 직군 전체를 순회
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime

from .utils import matches_keywords, make_job_id

COMPANY = "카카오"

API_URL = "https://careers.kakao.com/public/api/job-list"
DETAIL_URL = "https://careers.kakao.com/jobs/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko",
    "Referer": "https://careers.kakao.com/jobs",
}


def crawl(config):
    """카카오 채용 API를 직군별로 호출해 검색어에 맞는 공고만 반환."""
    print(f"\n🔍 {COMPANY} 크롤링 시작...")
    jobs = []
    max_pages = config.get("max_pages", 5)

    try:
        # 1) 첫 호출로 전체 직군(jobType) 목록 확보
        first = _fetch(part="", page=1)
        job_types = [
            t.get("jobType")
            for t in (first.get("jobTypeCountDtoList") or [])
            if t.get("jobType")
        ] or ["TECHNOLOGY", "DESIGN", "BUSINESS_SERVICES", "STAFF"]

        # 2) 직군별로 페이지 순회
        for part in job_types:
            data = _fetch(part=part, page=1)
            total_page = min(data.get("totalPage", 1), max_pages)

            for page in range(1, total_page + 1):
                if page > 1:
                    data = _fetch(part=part, page=page)
                for job in data.get("jobList") or []:
                    parsed = _parse_job(job)
                    if parsed and matches_keywords(parsed["title"], config):
                        jobs.append(parsed)

        # id 기준 중복 제거 (직군 경계에서 중복 노출 대비)
        unique = {j["id"]: j for j in jobs}
        jobs = list(unique.values())
        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _fetch(part, page):
    """목록 API 1회 호출 → JSON dict."""
    params = {
        "company": "KAKAO",
        "part": part,
        "page": page,
        "skillSet": "",
        "employeeType": "",
        "keyword": "",
    }
    response = requests.get(API_URL, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def _parse_job(job):
    """카카오 API 응답 1건 → 표준 공고 dict. 실패 시 None."""
    title = (job.get("jobOfferTitle") or "").strip()
    if not title:
        return None

    # 계열사명(companyName)이 제목에 없으면 접두로 추가
    company_name = (job.get("companyName") or "").strip()
    if company_name and company_name not in title and company_name != COMPANY:
        title = f"[{company_name}] {title}"

    real_id = job.get("realId")
    if not real_id:
        return None
    job_url = DETAIL_URL.format(real_id)

    posted_date = _parse_dt(job.get("regDate"))
    end_date = _parse_dt(job.get("endDate"))  # 상시채용이면 null → None

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": posted_date or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "end_date": end_date,
    }


def _parse_dt(value):
    """'2026-06-23T10:02:37' 형식 → ISO. 실패 시 None."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 채용공고 크롤러 (JSON API 직접 호출)
- 목록 페이지가 무한스크롤(AJAX)로 동작 → 백엔드 API를 직접 호출
- 목록 API: https://recruit.navercorp.com/rcrt/loadJobList.do
  (공개 엔드포인트, GET. firstIndex로 페이지네이션, 응답은 UTF-8 JSON)
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime

from .utils import matches_keywords, make_job_id

COMPANY = "네이버"

API_URL = "https://recruit.navercorp.com/rcrt/loadJobList.do"
DETAIL_URL = "https://recruit.navercorp.com/rcrt/view.do?annoId={}"
PAGE_SIZE = 10  # 목록 API가 한 번에 반환하는 건수


def crawl(config):
    """네이버 채용 API를 호출해 검색어에 맞는 공고만 반환."""
    print(f"\n🔍 {COMPANY} 크롤링 시작...")
    jobs = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ko",
        "Referer": "https://recruit.navercorp.com/rcrt/list.do",
        "X-Requested-With": "XMLHttpRequest",
    }

    max_pages = config.get("max_pages", 5)

    try:
        for page in range(max_pages):
            params = {
                "annoId": "",
                "sw": "",
                "subJobCdArr": "",
                "sysCompanyCdArr": "",
                "empTypeCdArr": "",
                "entTypeCdArr": "",
                "workAreaCdArr": "",
                "firstIndex": page * PAGE_SIZE,
            }

            response = requests.get(API_URL, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            response.encoding = "utf-8"
            data = response.json()
            job_list = data.get("list") or []

            if not job_list:
                break

            for job in job_list:
                parsed = _parse_job(job)
                if parsed and matches_keywords(parsed["title"], config):
                    jobs.append(parsed)

            # totalSize 기준 마지막 페이지면 중단
            total = data.get("totalSize", 0)
            if (page + 1) * PAGE_SIZE >= total:
                break

        # id 기준 중복 제거
        unique = {j["id"]: j for j in jobs}
        jobs = list(unique.values())
        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _parse_job(job):
    """네이버 API 응답 1건 → 표준 공고 dict. 실패 시 None."""
    title = (job.get("annoSubject") or "").strip()
    if not title:
        return None

    # 계열사명(sysCompanyCdNm)이 제목에 없으면 접두로 추가
    company_name = (job.get("sysCompanyCdNm") or "").strip()
    if company_name and company_name not in title:
        title = f"[{company_name}] {title}"

    anno_id = job.get("annoId")
    if not anno_id:
        return None
    job_url = job.get("jobDetailLink") or DETAIL_URL.format(anno_id)

    posted_date = _parse_dt(job.get("staYmdTime"))
    end_date = _parse_dt(job.get("endYmdTime"))
    # 상시모집(2999.12.31) / 채용시 마감(2099.12.31)은 마감일 없음 처리
    if end_date and end_date[:4] in ("2999", "2099"):
        end_date = None

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": posted_date or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "end_date": end_date,
    }


def _parse_dt(value):
    """'2026.06.15 14:00:00' 형식 → ISO. 날짜만 있어도 처리. 실패 시 None."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None

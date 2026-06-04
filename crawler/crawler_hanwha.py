#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
한화 채용공고 크롤러 (JSON API 직접 호출)
- 사이트가 Vue SPA로 개편되어 HTML 파싱 불가 → 백엔드 API 사용
- 목록 API: https://hwadm.hanwhain.com/new-backend/portal/api/rcRecruit/search-rcrt
  (공개 엔드포인트, POST JSON. 프런트 axios baseURL이 hwadm 호스트)
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime

from .utils import matches_keywords, make_job_id

COMPANY = "한화"

API_URL = "https://hwadm.hanwhain.com/new-backend/portal/api/rcRecruit/search-rcrt"
DETAIL_URL = "https://www.hanwhain.com/portal/apply/recruit/detail?rtSeq={}"


def crawl(config):
    """한화 채용 API를 호출해 검색어에 맞는 공고만 반환."""
    print(f"\n🔍 {COMPANY} 크롤링 시작...")
    jobs = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko",
        "Origin": "https://www.hanwhain.com",
        "Referer": "https://www.hanwhain.com/",
    }

    max_pages = config.get("max_pages", 5)

    try:
        for page in range(max_pages):  # API는 0-base 페이지
            params = {
                "langCd": "KR",
                "searchText": "",
                "sdSeqList": None,   # 계열사 전체
                "rtNrcrtYn": "",
                "rtCarrYn": "",
                "rtIntnYn": "",
                "rtPermanentWorkYn": "",
                "rtTempWorkYn": "",
                "djSeqList": None,
                "rjSeqList": None,
                "page": page,
                "size": 100,
            }

            response = requests.post(API_URL, headers=headers, json=params, timeout=15)
            response.raise_for_status()
            data = response.json().get("data", {}) or {}
            job_list = data.get("list") or []

            if not job_list:
                break

            for job in job_list:
                parsed = _parse_job(job)
                if parsed and matches_keywords(parsed["title"], config):
                    jobs.append(parsed)

            if not data.get("hasNext"):
                break

        # id 기준 중복 제거 (계열사 중복 노출 대비)
        unique = {j["id"]: j for j in jobs}
        jobs = list(unique.values())
        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _parse_job(job):
    """한화 API 응답 1건 → 표준 공고 dict. 실패 시 None."""
    title = (job.get("rtNm") or "").strip()
    if not title:
        return None

    # 계열사명(sdNm)이 제목에 없으면 접두로 추가
    company_name = (job.get("sdNm") or "").strip()
    if company_name and company_name not in title:
        title = f"[{company_name}] {title}"

    rt_seq = job.get("rtSeq")
    if not rt_seq:
        return None
    job_url = DETAIL_URL.format(rt_seq)

    posted_date = _parse_dt(job.get("rtAcptStrtDttm"))
    end_date = _parse_dt(job.get("rtAcptEndDttm"))

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": posted_date or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "end_date": end_date,
    }


def _parse_dt(value):
    """'2026.05.28 09:00' 형식 → ISO. 날짜만 있으면 그것도 처리. 실패 시 None."""
    if not value:
        return None
    value = value.strip()
    for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LG 채용공고 크롤러 (JSON API 직접 호출)
- 출처: https://api.careers.lg.com/rmk/job/retrieveJobNoticesList
- 먼저 careers.lg.com/apply 를 방문해 세션 쿠키를 받은 뒤 API 호출
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime

from .utils import matches_keywords, make_job_id

COMPANY = "LG"


def crawl(config):
    """LG 채용 API를 호출해 검색어에 맞는 공고만 반환."""
    print(f"\n🔍 {COMPANY} 크롤링 시작...")
    jobs = []

    url = "https://api.careers.lg.com/rmk/job/retrieveJobNoticesList"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko,en;q=0.9,en-US;q=0.8",
        "Content-Type": "application/json",
        "Origin": "https://careers.lg.com",
        "Referer": "https://careers.lg.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    payload = {
        "lnbSearch": "",
        "hashTagText": "",
        "recDate": "POST_START_DATE",
        "order": "DESC",
        "careerList": [],
        "companyCodeList": [],
        "desireLocList": [],
        "jobGroupList": [],
    }

    try:
        session = requests.Session()
        # 세션 쿠키 획득용 사전 방문
        session.get(
            "https://careers.lg.com/apply",
            headers={"User-Agent": headers["User-Agent"]},
            timeout=10,
        )

        response = session.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()

        job_list = _extract_list(result)
        if not job_list:
            print("   ⚠️ 공고를 찾을 수 없습니다.")
            return jobs

        for job in job_list:
            parsed = _parse_job(job)
            if parsed and matches_keywords(parsed["title"], config):
                jobs.append(parsed)

        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _extract_list(result):
    """LG 응답에서 공고 리스트를 꺼냄 (응답 구조 변동 대비)."""
    if isinstance(result.get("data"), dict):
        data = result["data"]
        return (
            data.get("jobNoticeList", [])
            or data.get("list", [])
            or data.get("items", [])
        )
    if isinstance(result.get("data"), list):
        return result["data"]
    return result.get("jobNoticeList") or result.get("list") or []


def _parse_job(job):
    """LG API 응답 1건 → 표준 공고 dict. 실패 시 None."""
    title = (
        job.get("jobNoticeName") or job.get("title") or job.get("name") or ""
    ).strip()
    if not title:
        return None

    company_name = (
        job.get("companyName") or job.get("company") or job.get("companyNm") or ""
    ).strip()
    if company_name and company_name not in title:
        title = f"[{company_name}] {title}"

    job_id = (
        job.get("jobNoticeId")
        or job.get("id")
        or job.get("noticeId")
        or job.get("jobNoticesSeq")
        or ""
    )
    if not job_id:
        return None
    job_url = f"https://careers.lg.com/apply/detail?id={job_id}"

    end_date = _parse_lg_date(job.get("recEndDateTime") or "")

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "end_date": end_date,
    }


def _parse_lg_date(value):
    """'2026.03.15 23:00' 형식 → ISO. 실패 시 None."""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y.%m.%d %H:%M")
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None

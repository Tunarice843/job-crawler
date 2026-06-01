#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SK 채용공고 크롤러 (JSON API 직접 호출)
- 출처: https://www.skcareers.com/Recruit/GetRecruitList
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime

from .utils import matches_keywords, make_job_id

COMPANY = "SK"


def crawl(config):
    """SK 채용 API를 호출해 검색어에 맞는 공고만 반환."""
    print(f"\n🔍 {COMPANY} 크롤링 시작...")
    jobs = []

    url = "https://www.skcareers.com/Recruit/GetRecruitList"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.skcareers.com/Recruit/Index",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }

    max_pages = config.get("max_pages", 5)

    try:
        for page in range(1, max_pages + 1):
            data = {
                "sort": "2",
                "searchText": "",
                "corpCode": "",
                "jobRole": "0",
                "page": str(page),
                "startDt": "",
                "endDt": "",
            }

            response = requests.post(url, headers=headers, data=data, timeout=15)
            response.raise_for_status()
            result = response.json()
            job_list = result.get("list", []) or result.get("List", [])

            if not job_list:
                break

            for job in job_list:
                parsed = _parse_job(job)
                if parsed and matches_keywords(parsed["title"], config):
                    jobs.append(parsed)

            if len(job_list) < 10:  # 마지막 페이지로 판단
                break

        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _parse_job(job):
    """SK API 응답 1건 → 표준 공고 dict. 실패 시 None."""
    title = (
        job.get("title")
        or job.get("recruitTitle")
        or job.get("postingTitle")
        or ""
    ).strip()
    if not title:
        return None

    company_name = (
        job.get("corpName") or job.get("companyName") or job.get("company") or ""
    ).strip()
    if company_name and company_name not in title:
        title = f"[{company_name}] {title}"

    recruit_no = (
        job.get("noticeID")
        or job.get("jobNoticeNo")
        or job.get("recruit_no")
        or job.get("recruitNo")
        or job.get("no")
        or job.get("id")
        or ""
    )
    if not recruit_no:
        return None
    recruit_no = str(recruit_no).replace(",", "").strip()
    if not recruit_no.startswith("R"):
        recruit_no = f"R{recruit_no}"
    job_url = f"https://www.skcareers.com/Recruit/Detail/{recruit_no}"

    posted_date = _parse_en_date(job.get("start") or job.get("postDate") or "")
    end_date = _parse_en_date(job.get("end") or "", end_of_day=True)

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": posted_date or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "end_date": end_date,
    }


def _parse_en_date(value, end_of_day=False):
    """'June 1, 2026' 형식 → ISO. 실패 시 None."""
    if not value:
        return None
    try:
        date_str = value.split("(")[0].strip()
        parsed = datetime.strptime(date_str, "%B %d, %Y")
        fmt = "%Y-%m-%dT23:59:59" if end_of_day else "%Y-%m-%dT00:00:00"
        return parsed.strftime(fmt)
    except Exception:
        return None

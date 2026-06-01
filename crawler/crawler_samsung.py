#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
삼성 채용공고 크롤러 (HTML 파싱, 페이지네이션 지원)
- 출처: https://www.samsungcareers.com/hr/list.data
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime
from bs4 import BeautifulSoup

from .utils import matches_keywords, make_job_id

COMPANY = "삼성"


def crawl(config):
    """삼성 채용 페이지를 파싱해 검색어에 맞는 공고만 반환."""
    print(f"\n🔍 {COMPANY} 크롤링 시작...")
    jobs = []

    url = "https://www.samsungcareers.com/hr/list.data"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.samsungcareers.com/hr/",
    }

    max_pages = config.get("max_pages", 5)
    previous_ids = set()

    try:
        for page in range(1, max_pages + 1):
            data = {
                "currentPageNo": str(page),
                "intNo": "0",
                "strVal": "",
                "strTxt": "",
                "strKey": "",
                "strCompany": "",
                "strType": "",
                "strOrderBy": "",
                "strEntity": "",
            }

            response = requests.post(url, headers=headers, data=data, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("li")
            if not items:
                break

            # 같은 페이지가 반복되면(더 이상 다음 페이지 없음) 중단
            current_ids = set()
            for item in items:
                link = item.find("a")
                if link:
                    current_ids.add(link.get("data-value", "").strip().replace(",", ""))
            if page > 1 and current_ids == previous_ids:
                break
            previous_ids = current_ids

            for item in items:
                parsed = _parse_item(item)
                if parsed and matches_keywords(parsed["title"], config):
                    jobs.append(parsed)

            if len(items) < 9:  # 마지막 페이지로 판단
                break

        # 같은 공고가 여러 페이지에 중복 노출될 수 있어 id로 정리
        unique = {j["id"]: j for j in jobs}
        jobs = list(unique.values())
        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ 페이지 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _parse_item(item):
    """삼성 공고 <li> 1건 → 표준 공고 dict. 실패 시 None."""
    title_elem = item.find("h3", class_="title")
    if not title_elem:
        return None
    title = title_elem.get_text(strip=True)
    if not title:
        return None

    company_elem = item.find("p", class_="company")
    company_name = company_elem.get_text(strip=True) if company_elem else ""
    if company_name and company_name not in title:
        title = f"[{company_name}] {title}"

    link = item.find("a")
    if not link:
        return None
    job_id = link.get("data-value", "").strip().replace(",", "")
    if not job_id:
        return None
    job_url = f"https://www.samsungcareers.com/hr/?no={job_id}"

    posted_date, end_date = None, None
    period_elem = item.find("span", class_="period")
    if period_elem:
        parts = period_elem.get_text(strip=True).split("~")
        posted_date = _parse_dot_date(parts[0]) if parts else None
        if len(parts) > 1:
            end_date = _parse_dot_date(parts[1], end_of_day=True)

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": posted_date or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "end_date": end_date,
    }


def _parse_dot_date(value, end_of_day=False):
    """'2026.06.01' 형식 → ISO. 실패 시 None."""
    try:
        parsed = datetime.strptime(value.strip(), "%Y.%m.%d")
        fmt = "%Y-%m-%dT23:59:59" if end_of_day else "%Y-%m-%dT00:00:00"
        return parsed.strftime(fmt)
    except Exception:
        return None

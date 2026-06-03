#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기아차 채용공고 크롤러 (JSON API 직접 호출, 페이지네이션 지원)
- 출처: https://career.kia.com/api/rec/AP-KM-FO-02700  (X-HKMC-SERVICE: KM)
- 검색어 필터는 config.json 기준으로 crawl 시점에 적용
"""

import requests
from datetime import datetime

from .utils import matches_keywords, make_job_id

COMPANY = "기아차"


def crawl(config):
    """기아차 채용 API를 호출해 검색어에 맞는 공고만 반환."""
    print(f"\n🚗 {COMPANY} 크롤링 시작...")
    jobs = []

    url = "https://career.kia.com/api/rec/AP-KM-FO-02700"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko,en;q=0.9,en-US;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://career.kia.com/apply/applyList.kc",
        "X-HKMC-SERVICE": "KM",
        "X-HKMC-TOKEN": "null",
        "X-HKMC-EMP-TOKEN": "null",
    }

    max_pages = config.get("max_pages", 5)

    try:
        for page in range(1, max_pages + 1):
            params = {
                "hgrCd": "2",
                "lang": "ko",
                "page": str(page),
                "pageblock": "100",
                "searchSectorList": "",
                "searchSecList": "",
                "searchPlaceList": "",
                "searchText": "",
            }

            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            job_list = _extract_list(response.json())

            if not job_list:
                break

            for job in job_list:
                parsed = _parse_job(job)
                if parsed and matches_keywords(parsed["title"], config):
                    jobs.append(parsed)

            if len(job_list) < 100:  # 마지막 페이지로 판단
                break

        # 같은 공고가 중복 노출될 수 있어 id로 정리
        unique = {j["id"]: j for j in jobs}
        jobs = list(unique.values())
        print(f"   📊 검색어 일치: {len(jobs)}개")

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 호출 실패: {e}")
    except Exception as e:
        print(f"   ❌ 크롤링 실패: {e}")

    return jobs


def _extract_list(result):
    """기아 응답에서 공고 리스트를 꺼냄 (응답 구조 변동 대비)."""
    if isinstance(result.get("data"), dict):
        data = result["data"]
        return (
            data.get("list", [])
            or data.get("items", [])
            or data.get("recruitList", [])
        )
    if isinstance(result.get("data"), list):
        return result["data"]
    return result.get("list") or result.get("recruitList") or []


def _parse_job(job):
    """기아 API 응답 1건 → 표준 공고 dict. 실패 시 None."""
    title = (
        job.get("recuNoticeNm")
        or job.get("recuTitle")
        or job.get("title")
        or job.get("recruitTitle")
        or job.get("name")
        or ""
    ).strip()
    if not title:
        return None

    company_name = (
        job.get("companyName")
        or job.get("company")
        or job.get("corpName")
        or job.get("recuCmpnNm")
        or COMPANY
    ).strip()
    if company_name and company_name not in title:
        title = f"[{company_name}] {title}"

    # 상세 URL 구성에 필요한 3개 키가 모두 있어야 함
    recu_yy = job.get("recuYy", "")
    recu_type = job.get("recuType", "")
    recu_cls = job.get("recuCls", "")
    if not all([recu_yy, recu_type, recu_cls]):
        return None
    job_url = (
        "https://career.kia.com/apply/applyView.kc"
        f"?recuYy={recu_yy}&recuType={recu_type}&recuCls={recu_cls}"
    )

    posted_date = (
        _parse_compact_date(job.get("regDm"))
        or _parse_compact_date(job.get("applyStartDt"))
        or _parse_compact_date(job.get("appDispStDt"))
        or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    )
    end_date = (
        _parse_compact_date(job.get("applyEndDt"), end_of_day=True)
        or _parse_compact_date(job.get("opsEndDt"), end_of_day=True)
        or _parse_compact_date(job.get("appDispEndDt"), end_of_day=True)
        or _parse_compact_date(job.get("recuEndDt"), end_of_day=True)
    )

    return {
        "id": make_job_id(COMPANY, title),
        "company": COMPANY,
        "title": title,
        "url": job_url,
        "posted_date": posted_date,
        "end_date": end_date,
    }


def _parse_compact_date(value, end_of_day=False):
    """'20260315' 형식(YYYYMMDD) → ISO. 실패 시 None."""
    if not value or len(str(value)) < 8:
        return None
    s = str(value)
    time_part = "23:59:59" if end_of_day else "00:00:00"
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}T{time_part}"

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
크롤러 통합 실행 진입점.

실행:  python -m crawler.run        (프로젝트 루트에서)

동작:
  1) config.json 로드 (검색어 / 활성 회사 / 출력 경로)
  2) 활성화된 회사만 크롤링 (검색어 필터는 각 크롤러 내부에서 적용)
  3) 기존 jobs.json과 병합 + ID 기준 중복 제거
  4) docs/data/jobs.json 으로 저장 → GitHub Pages가 이 파일을 읽어 표시
"""

import sys
from datetime import datetime

# Windows 콘솔(cp949)에서도 이모지/한글 출력이 깨지지 않도록 UTF-8 강제
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from .utils import load_config, load_existing_jobs, save_jobs
from . import (
    crawler_sk,
    crawler_samsung,
    crawler_lg,
    crawler_hyundai,
    crawler_kia,
)

# 회사 키 → 크롤 함수 매핑 (새 포털 추가 시 여기에 한 줄 등록)
CRAWLERS = {
    "sk": crawler_sk.crawl,
    "samsung": crawler_samsung.crawl,
    "lg": crawler_lg.crawl,
    "hyundai": crawler_hyundai.crawl,
    "kia": crawler_kia.crawl,
}


def main():
    config = load_config()
    output_path = config.get("output_path", "docs/data/jobs.json")

    keywords = config.get("keywords") or []
    print("=" * 60)
    print("🚀 채용공고 크롤러 실행")
    print(f"   검색어({config.get('keyword_match', 'any')}): "
          f"{', '.join(keywords) if keywords else '(전체 수집)'}")
    print("=" * 60)

    # 기존 공고 로드 (재크롤링 후에도 누적 유지)
    existing_jobs, seen_ids = load_existing_jobs(output_path)
    print(f"📋 기존 공고: {len(existing_jobs)}개")

    merged = list(existing_jobs)
    new_count = 0

    enabled = config.get("companies", {})
    for key, crawl_fn in CRAWLERS.items():
        if not enabled.get(key, False):
            continue
        for job in crawl_fn(config):
            if job["id"] in seen_ids:  # set 기반 빠른 중복 체크
                continue
            seen_ids.add(job["id"])
            merged.append(job)
            new_count += 1

    print("=" * 60)
    print(f"📊 신규 공고 {new_count}개 추가 (총 {len(merged)}개)")
    print("=" * 60)

    save_jobs(output_path, merged, datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    print("🏁 완료")


if __name__ == "__main__":
    main()

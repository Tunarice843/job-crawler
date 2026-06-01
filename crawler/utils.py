#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 유틸리티
- 설정/저장 파일 로드
- 검색어(키워드) 매칭  ← config.json에서 편집, 크롤링 시점에 적용
- 안정적인 공고 ID 생성 (대시보드 localStorage 상태 유지를 위해)
- 빠른 중복 체크 (set 기반)
"""

import json
import os
import hashlib

# 프로젝트 루트 (이 파일의 한 단계 위 디렉터리)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve(path):
    """상대 경로를 프로젝트 루트 기준 절대 경로로 변환."""
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def load_config():
    """config.json 로드."""
    config_path = _resolve("config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ config.json 파일이 없습니다! 프로젝트 루트에 생성해주세요.")
        raise


def matches_keywords(title, config):
    """
    config.json의 검색어 규칙에 따라 제목이 수집 대상인지 판단.

    - keywords 가 비어 있으면 모든 공고를 수집 (필터 없음)
    - keyword_match: "any"(하나라도 포함) | "all"(모두 포함)
    - case_sensitive: 대소문자 구분 여부
    """
    keywords = config.get("keywords") or []
    if not keywords:
        return True  # 키워드 미설정 시 전체 수집

    text = title if config.get("case_sensitive") else title.lower()
    norm = (lambda k: k) if config.get("case_sensitive") else (lambda k: k.lower())
    hits = [kw for kw in keywords if norm(kw) in text]

    if config.get("keyword_match", "any") == "all":
        return len(hits) == len(keywords)
    return len(hits) > 0


def make_job_id(company, title):
    """
    회사명 + 제목으로 안정적인(매 실행 동일한) ID 생성.
    대시보드의 '확인 완료'·'책갈피' 상태가 재크롤링 후에도 유지되도록 함.
    """
    raw = f"{company}|{title}".encode("utf-8")
    return "job_" + hashlib.md5(raw).hexdigest()[:16]


def load_existing_jobs(output_path):
    """기존 jobs.json 로드 → (공고 리스트, 중복체크용 ID set)."""
    path = _resolve(output_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        jobs = data.get("jobs", [])
        seen = {job.get("id") for job in jobs}
        return jobs, seen
    except (FileNotFoundError, json.JSONDecodeError):
        return [], set()


def save_jobs(output_path, jobs, updated_at):
    """공고 리스트를 jobs.json으로 저장 (게시일 기준 내림차순)."""
    path = _resolve(output_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    jobs_sorted = sorted(
        jobs, key=lambda j: j.get("posted_date") or "", reverse=True
    )
    payload = {
        "updated_at": updated_at,
        "count": len(jobs_sorted),
        "jobs": jobs_sorted,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"💾 {len(jobs_sorted)}개 공고 저장 → {path}")

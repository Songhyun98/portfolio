"""
수집기 공통 재시도/예외 처리 유틸리티

with_retry(fn, retries, label): 지수 백오프 + jitter로 fn 재시도
raise_for_status(response, context): HTTP 상태 검증

재시도 대상: RetryableError (429 / 5xx), ConnectionError, Timeout
비대상: 4xx (인증 오류, 잘못된 요청 등) → 즉시 예외
"""

import time
import random
import requests

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DEFAULT_RETRIES = 3
DEFAULT_TIMEOUT = 15  # seconds
_BASE_DELAY = 1.0


class RetryableError(Exception):
    """재시도 가능한 일시적 오류 (429 / 5xx / 네트워크)"""


def with_retry(fn, retries: int = DEFAULT_RETRIES, label: str = ""):
    """
    지수 백오프 + jitter로 fn을 최대 retries회 재시도.

    재시도 대상: RetryableError, ConnectionError, Timeout
    그 외 예외는 즉시 전파.
    """
    last_exc: Exception = RuntimeError("알 수 없는 오류")
    for attempt in range(retries + 1):
        try:
            return fn()
        except (RetryableError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            last_exc = e
            if attempt == retries:
                break
            delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
            tag = f"[{label}] " if label else ""
            print(f"  ⏳ {tag}재시도 {attempt + 1}/{retries} ({delay:.1f}s 후): {e}")
            time.sleep(delay)
    raise last_exc


def raise_for_status(response: requests.Response, context: str = "") -> None:
    """
    HTTP 응답 상태 검증.
    429 / 5xx → RetryableError (with_retry가 재시도)
    그 외 비200 → Exception (즉시 실패)
    """
    if response.status_code == 200:
        return
    prefix = f"{context}: " if context else ""
    if response.status_code in _RETRYABLE_STATUS:
        raise RetryableError(f"{prefix}HTTP {response.status_code} - {response.text[:300]}")
    raise Exception(f"{prefix}HTTP {response.status_code} - {response.text[:300]}")

#!/usr/bin/env python3
"""
Patch script for samsung_deep_buy_service.py
Adds tier cooldown mechanism to prevent cascading sells
"""
import re

# Read the file
filepath = 'backend/services/samsung_deep_buy_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add new class variables after existing locks
old_lock_vars = '''    # 매수 락 (동시 매수 방지)
    _buy_locks: Dict[str, datetime] = {}
    _buy_lock_mutex = threading.RLock()  # RLock for reentrant locking
    BUY_LOCK_SECONDS = 60  # 매수 후 60초간 재매수 차단'''

new_lock_vars = '''    # 매수 락 (동시 매수 방지)
    _buy_locks: Dict[str, datetime] = {}
    _buy_lock_mutex = threading.RLock()  # RLock for reentrant locking
    BUY_LOCK_SECONDS = 60  # 매수 후 60초간 재매수 차단

    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 수익률이 이전 티어 아래로 떨어졌다가 다시 상승해야 함
    _last_tier_threshold: Dict[str, float] = {}  # 마지막 매도 티어 임계값
    _tier_cooldown_cleared: Dict[str, bool] = {}  # 쿨다운 해제 여부 (수익률 하락 감지)
    _tier_mutex = threading.RLock()'''

if old_lock_vars in content:
    content = content.replace(old_lock_vars, new_lock_vars)
    print('Step 1 완료: 클래스 변수 추가')
else:
    print('Step 1 실패: 클래스 변수 위치를 찾을 수 없음')

# 2. Add new methods for tier cooldown management after release_sell_lock method
old_method_end = '''    @classmethod
    def release_sell_lock(cls, stock_code: str):
        """매도 락 해제"""
        with cls._lock_mutex:
            if stock_code in cls._sell_locks:
                del cls._sell_locks[stock_code]
                logger.info(f"[딥바이] {stock_code} 매도 락 해제")

    # ===== 매수 락 메서드 ====='''

new_method_end = '''    @classmethod
    def release_sell_lock(cls, stock_code: str):
        """매도 락 해제"""
        with cls._lock_mutex:
            if stock_code in cls._sell_locks:
                del cls._sell_locks[stock_code]
                logger.info(f"[딥바이] {stock_code} 매도 락 해제")

    # ===== [v2.4] 티어 쿨다운 메서드 =====
    @classmethod
    def set_tier_threshold(cls, stock_code: str, threshold: float):
        """마지막 매도 티어 임계값 설정 (매도 후 호출)"""
        with cls._tier_mutex:
            cls._last_tier_threshold[stock_code] = threshold
            cls._tier_cooldown_cleared[stock_code] = False  # 쿨다운 시작
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 설정: {threshold}% 아래로 떨어져야 다음 티어 실행 가능")

    @classmethod
    def check_tier_cooldown(cls, stock_code: str, current_profit_rate: float) -> bool:
        """
        티어 쿨다운 체크 및 업데이트
        - 수익률이 마지막 티어 임계값 아래로 떨어지면 쿨다운 해제
        - Returns: True if next tier is allowed, False otherwise
        """
        with cls._tier_mutex:
            # 첫 매도거나 쿨다운 정보 없으면 허용
            if stock_code not in cls._last_tier_threshold:
                return True
            
            threshold = cls._last_tier_threshold[stock_code]
            cooldown_cleared = cls._tier_cooldown_cleared.get(stock_code, True)
            
            # 이미 쿨다운 해제됨
            if cooldown_cleared:
                return True
            
            # 수익률이 임계값 아래로 떨어졌는지 확인
            if current_profit_rate < threshold:
                cls._tier_cooldown_cleared[stock_code] = True
                logger.info(f"[딥바이] {stock_code} 티어 쿨다운 해제: 수익률 {current_profit_rate:.2f}% < 임계값 {threshold}%")
                return True
            
            # 아직 쿨다운 중
            return False

    @classmethod
    def clear_tier_cooldown(cls, stock_code: str):
        """티어 쿨다운 초기화 (장 시작 시 또는 수동 리셋)"""
        with cls._tier_mutex:
            if stock_code in cls._last_tier_threshold:
                del cls._last_tier_threshold[stock_code]
            if stock_code in cls._tier_cooldown_cleared:
                del cls._tier_cooldown_cleared[stock_code]
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 초기화")

    # ===== 매수 락 메서드 ====='''

if old_method_end in content:
    content = content.replace(old_method_end, new_method_end)
    print('Step 2 완료: 티어 쿨다운 메서드 추가')
else:
    print('Step 2 실패: 메서드 위치를 찾을 수 없음')

# Write the modified content
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('패치 파일 저장 완료')

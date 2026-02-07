#!/usr/bin/env python3
"""
Patch script for samsung_deep_buy_service.py
Change tier cooldown from profit-based to time-based (30 minutes between tier sells)
"""

filepath = 'backend/services/samsung_deep_buy_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update class variables - add TIER_COOLDOWN_SECONDS and simplify tracking
old_tier_vars = '''    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 수익률이 이전 티어 아래로 떨어졌다가 다시 상승해야 함
    _last_tier_threshold: Dict[str, float] = {}  # 마지막 매도 티어 임계값
    _tier_cooldown_cleared: Dict[str, bool] = {}  # 쿨다운 해제 여부 (수익률 하락 감지)
    _tier_mutex = threading.RLock()'''

new_tier_vars = '''    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 이전 매도 후 30분 경과 필요
    _last_tier_sell_time: Dict[str, datetime] = {}  # 마지막 티어 매도 시간
    _tier_mutex = threading.RLock()
    TIER_COOLDOWN_SECONDS = 1800  # 티어 간 30분 간격 필요'''

if old_tier_vars in content:
    content = content.replace(old_tier_vars, new_tier_vars)
    print('Step 1 완료: 클래스 변수 업데이트')
else:
    print('Step 1 실패: 클래스 변수를 찾을 수 없음')

# 2. Update tier cooldown methods
old_methods = '''    # ===== [v2.4] 티어 쿨다운 메서드 =====
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
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 초기화")'''

new_methods = '''    # ===== [v2.4] 티어 쿨다운 메서드 (시간 기반) =====
    @classmethod
    def set_tier_sell_time(cls, stock_code: str):
        """티어 매도 시간 기록 (매도 후 호출)"""
        with cls._tier_mutex:
            cls._last_tier_sell_time[stock_code] = datetime.now()
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 시작: {cls.TIER_COOLDOWN_SECONDS}초 후 다음 티어 실행 가능")

    @classmethod
    def check_tier_cooldown(cls, stock_code: str, current_profit_rate: float = 0) -> bool:
        """
        티어 쿨다운 체크 (시간 기반)
        - 마지막 매도 후 TIER_COOLDOWN_SECONDS 경과해야 다음 티어 실행 가능
        - Returns: True if next tier is allowed, False otherwise
        """
        with cls._tier_mutex:
            # 첫 매도거나 기록 없으면 허용
            if stock_code not in cls._last_tier_sell_time:
                return True
            
            last_sell_time = cls._last_tier_sell_time[stock_code]
            elapsed = (datetime.now() - last_sell_time).total_seconds()
            
            if elapsed >= cls.TIER_COOLDOWN_SECONDS:
                # 쿨다운 완료
                return True
            
            # 아직 쿨다운 중
            remaining = int(cls.TIER_COOLDOWN_SECONDS - elapsed)
            remaining_min = remaining // 60
            remaining_sec = remaining % 60
            logger.debug(f"[딥바이] {stock_code} 티어 쿨다운 중: {remaining_min}분 {remaining_sec}초 남음")
            return False

    @classmethod
    def clear_tier_cooldown(cls, stock_code: str):
        """티어 쿨다운 초기화 (장 시작 시 또는 수동 리셋)"""
        with cls._tier_mutex:
            if stock_code in cls._last_tier_sell_time:
                del cls._last_tier_sell_time[stock_code]
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 초기화")
    
    @classmethod
    def get_tier_cooldown_remaining(cls, stock_code: str) -> int:
        """티어 쿨다운 남은 시간 (초) 반환"""
        with cls._tier_mutex:
            if stock_code not in cls._last_tier_sell_time:
                return 0
            last_sell_time = cls._last_tier_sell_time[stock_code]
            elapsed = (datetime.now() - last_sell_time).total_seconds()
            remaining = max(0, int(cls.TIER_COOLDOWN_SECONDS - elapsed))
            return remaining'''

if old_methods in content:
    content = content.replace(old_methods, new_methods)
    print('Step 2 완료: 티어 쿨다운 메서드 업데이트')
else:
    print('Step 2 실패: 메서드를 찾을 수 없음')

# 3. Update cooldown check log message
old_cooldown_check = '''        # [v2.4] 티어 쿨다운 체크 - 연속 티어 매도 방지
        # 수익률이 이전 티어 아래로 떨어져야 다음 티어 실행 가능
        tier_cooldown_ok = cls.check_tier_cooldown(stock_code, profit_rate)
        if not tier_cooldown_ok:
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (티어 쿨다운 - 하락 대기)"
            logger.info(f"[딥바이] {stock_name}: 티어 쿨다운 중 - 수익률이 이전 티어 아래로 떨어져야 다음 매도 가능")
            return result'''

new_cooldown_check = '''        # [v2.4] 티어 쿨다운 체크 - 연속 티어 매도 방지 (30분 간격)
        tier_cooldown_ok = cls.check_tier_cooldown(stock_code, profit_rate)
        if not tier_cooldown_ok:
            remaining = cls.get_tier_cooldown_remaining(stock_code)
            remaining_min = remaining // 60
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (티어 쿨다운 - {remaining_min}분 대기)"
            logger.info(f"[딥바이] {stock_name}: 티어 쿨다운 중 - {remaining_min}분 후 다음 매도 가능")
            return result'''

if old_cooldown_check in content:
    content = content.replace(old_cooldown_check, new_cooldown_check)
    print('Step 3 완료: 쿨다운 체크 로그 업데이트')
else:
    print('Step 3 실패: 쿨다운 체크를 찾을 수 없음')

# 4. Update tier threshold setting to time-based
old_tier_set = '''            # [v2.4] 티어 쿨다운 설정 - 다음 티어 실행을 위해 수익률이 현재 티어 아래로 떨어져야 함
            cls.set_tier_threshold(stock_code, tier_pct)'''

new_tier_set = '''            # [v2.4] 티어 쿨다운 설정 - 다음 티어까지 30분 대기
            cls.set_tier_sell_time(stock_code)'''

if old_tier_set in content:
    content = content.replace(old_tier_set, new_tier_set)
    print('Step 4 완료: 티어 설정 호출 업데이트')
else:
    print('Step 4 실패: 티어 설정 호출을 찾을 수 없음')

# Write the modified content
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n패치 완료! 새 로직:')
print('- 티어 매도 후 30분 쿨다운')
print('- 30분 후 다음 티어 수익률 도달 시 매도')

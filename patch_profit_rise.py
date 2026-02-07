#!/usr/bin/env python3
"""
Patch script for samsung_deep_buy_service.py
Change tier cooldown to profit-rise-based (only execute next tier if profit increased)
"""

filepath = 'backend/services/samsung_deep_buy_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update class variables - change to profit-based tracking
old_tier_vars = '''    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 이전 매도 후 30분 경과 필요
    _last_tier_sell_time: Dict[str, datetime] = {}  # 마지막 티어 매도 시간
    _tier_mutex = threading.RLock()
    TIER_COOLDOWN_SECONDS = 1800  # 티어 간 30분 간격 필요'''

new_tier_vars = '''    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 수익률이 마지막 매도 시점보다 상승해야 함
    _last_sell_profit: Dict[str, float] = {}  # 마지막 티어 매도 시 수익률
    _tier_mutex = threading.RLock()'''

if old_tier_vars in content:
    content = content.replace(old_tier_vars, new_tier_vars)
    print('Step 1 완료: 클래스 변수 업데이트')
else:
    print('Step 1 실패: 클래스 변수를 찾을 수 없음')

# 2. Update tier cooldown methods
old_methods = '''    # ===== [v2.4] 티어 쿨다운 메서드 (시간 기반) =====
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

new_methods = '''    # ===== [v2.4] 티어 쿨다운 메서드 (수익률 상승 기반) =====
    @classmethod
    def set_last_sell_profit(cls, stock_code: str, profit_rate: float):
        """마지막 매도 시 수익률 기록"""
        with cls._tier_mutex:
            cls._last_sell_profit[stock_code] = profit_rate
            logger.info(f"[딥바이] {stock_code} 마지막 매도 수익률 기록: {profit_rate:.2f}%")

    @classmethod
    def check_tier_cooldown(cls, stock_code: str, current_profit_rate: float) -> bool:
        """
        티어 쿨다운 체크 (수익률 상승 기반)
        - 현재 수익률이 마지막 매도 시점보다 높아야 다음 티어 실행 가능
        - Returns: True if next tier is allowed, False otherwise
        """
        with cls._tier_mutex:
            # 첫 매도거나 기록 없으면 허용
            if stock_code not in cls._last_sell_profit:
                return True
            
            last_profit = cls._last_sell_profit[stock_code]
            
            # 수익률이 상승했는지 확인 (0.1% 이상 상승해야 함 - 노이즈 방지)
            if current_profit_rate > last_profit + 0.1:
                logger.info(f"[딥바이] {stock_code} 수익률 상승 감지: {last_profit:.2f}% → {current_profit_rate:.2f}%")
                return True
            
            # 수익률이 상승하지 않음
            logger.debug(f"[딥바이] {stock_code} 수익률 미상승: 현재 {current_profit_rate:.2f}% <= 마지막 {last_profit:.2f}%")
            return False

    @classmethod
    def clear_tier_cooldown(cls, stock_code: str):
        """티어 쿨다운 초기화 (장 시작 시 또는 수동 리셋)"""
        with cls._tier_mutex:
            if stock_code in cls._last_sell_profit:
                del cls._last_sell_profit[stock_code]
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 초기화")
    
    @classmethod
    def get_last_sell_profit(cls, stock_code: str) -> float:
        """마지막 매도 시 수익률 반환 (없으면 0)"""
        with cls._tier_mutex:
            return cls._last_sell_profit.get(stock_code, 0.0)'''

if old_methods in content:
    content = content.replace(old_methods, new_methods)
    print('Step 2 완료: 티어 쿨다운 메서드 업데이트')
else:
    print('Step 2 실패: 메서드를 찾을 수 없음')

# 3. Update cooldown check log message
old_cooldown_check = '''        # [v2.4] 티어 쿨다운 체크 - 연속 티어 매도 방지 (30분 간격)
        tier_cooldown_ok = cls.check_tier_cooldown(stock_code, profit_rate)
        if not tier_cooldown_ok:
            remaining = cls.get_tier_cooldown_remaining(stock_code)
            remaining_min = remaining // 60
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (티어 쿨다운 - {remaining_min}분 대기)"
            logger.info(f"[딥바이] {stock_name}: 티어 쿨다운 중 - {remaining_min}분 후 다음 매도 가능")
            return result'''

new_cooldown_check = '''        # [v2.4] 티어 쿨다운 체크 - 수익률 상승 시에만 다음 티어 실행
        tier_cooldown_ok = cls.check_tier_cooldown(stock_code, profit_rate)
        if not tier_cooldown_ok:
            last_profit = cls.get_last_sell_profit(stock_code)
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (상승 대기 - 마지막 {last_profit:.1f}%)"
            logger.debug(f"[딥바이] {stock_name}: 수익률 미상승 - 현재 {profit_rate:.1f}% <= 마지막 {last_profit:.1f}%")
            return result'''

if old_cooldown_check in content:
    content = content.replace(old_cooldown_check, new_cooldown_check)
    print('Step 3 완료: 쿨다운 체크 로그 업데이트')
else:
    print('Step 3 실패: 쿨다운 체크를 찾을 수 없음')

# 4. Update tier setting to profit-based
old_tier_set = '''            # [v2.4] 티어 쿨다운 설정 - 다음 티어까지 30분 대기
            cls.set_tier_sell_time(stock_code)'''

new_tier_set = '''            # [v2.4] 마지막 매도 수익률 기록 - 이보다 상승해야 다음 티어 실행
            cls.set_last_sell_profit(stock_code, profit_rate)'''

if old_tier_set in content:
    content = content.replace(old_tier_set, new_tier_set)
    print('Step 4 완료: 티어 설정 호출 업데이트')
else:
    print('Step 4 실패: 티어 설정 호출을 찾을 수 없음')

# Write the modified content
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n패치 완료! 새 로직:')
print('- Tier 1 매도 @ 1.6% → 저장')
print('- 수익률 2.1%로 상승 → Tier 2 매도')
print('- 수익률 그대로 2.1% → 매도 안함')
print('- 수익률 2.6%로 상승 → Tier 3 매도')

#!/usr/bin/env python3
"""
Patch script to add last_sell_profit column to Holding model
and update samsung_deep_buy_service.py to use DB instead of memory
"""

# ============================================
# Step 1: Update Holding model
# ============================================
holding_file = 'backend/models/holding.py'
with open(holding_file, 'r', encoding='utf-8') as f:
    content = f.read()

old_strategy_line = '''    strategy = Column(String, default="standard") # 매수 전략 (standard, turnaround 등)'''

new_strategy_line = '''    strategy = Column(String, default="standard") # 매수 전략 (standard, turnaround 등)
    
    # [v2.4] 티어 쿨다운 (서버 재시작해도 유지)
    last_sell_profit = Column(Float, nullable=True)  # 마지막 티어 매도 시 수익률'''

if old_strategy_line in content:
    content = content.replace(old_strategy_line, new_strategy_line)
    with open(holding_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Step 1 완료: Holding 모델에 last_sell_profit 컬럼 추가')
else:
    print('Step 1 스킵: 이미 추가되었거나 위치를 찾을 수 없음')

# ============================================
# Step 2: Update samsung_deep_buy_service.py
# ============================================
service_file = 'backend/services/samsung_deep_buy_service.py'
with open(service_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 2-1: Update class variables - remove memory-based storage
old_tier_vars = '''    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 수익률이 마지막 매도 시점보다 상승해야 함
    _last_sell_profit: Dict[str, float] = {}  # 마지막 티어 매도 시 수익률
    _tier_mutex = threading.RLock()'''

new_tier_vars = '''    # [v2.4] 티어 쿨다운 (연속 티어 매도 방지)
    # 다음 티어 실행 조건: 수익률이 마지막 매도 시점보다 상승해야 함
    # DB 기반 저장 (Holding.last_sell_profit) - 서버 재시작해도 유지됨'''

if old_tier_vars in content:
    content = content.replace(old_tier_vars, new_tier_vars)
    print('Step 2-1 완료: 클래스 변수 업데이트 (메모리 → DB)')
else:
    print('Step 2-1 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# 2-2: Update set_last_sell_profit method
old_set_method = '''    # ===== [v2.4] 티어 쿨다운 메서드 (수익률 상승 기반) =====
    @classmethod
    def set_last_sell_profit(cls, stock_code: str, profit_rate: float):
        """마지막 매도 시 수익률 기록"""
        with cls._tier_mutex:
            cls._last_sell_profit[stock_code] = profit_rate
            logger.info(f"[딥바이] {stock_code} 마지막 매도 수익률 기록: {profit_rate:.2f}%")'''

new_set_method = '''    # ===== [v2.4] 티어 쿨다운 메서드 (수익률 상승 기반, DB 저장) =====
    @classmethod
    def set_last_sell_profit(cls, db: Session, stock_code: str, profit_rate: float, portfolio_id: int):
        """마지막 매도 시 수익률 기록 (DB 저장)"""
        try:
            holding = db.query(Holding).filter(
                Holding.portfolio_id == portfolio_id,
                Holding.stock_code == stock_code
            ).first()
            
            if holding:
                holding.last_sell_profit = profit_rate
                db.commit()
                logger.info(f"[딥바이] {stock_code} 마지막 매도 수익률 DB 저장: {profit_rate:.2f}%")
            else:
                logger.warning(f"[딥바이] {stock_code} Holding 없음 - 수익률 저장 실패")
        except Exception as e:
            logger.error(f"[딥바이] {stock_code} 수익률 저장 오류: {e}")
            db.rollback()'''

if old_set_method in content:
    content = content.replace(old_set_method, new_set_method)
    print('Step 2-2 완료: set_last_sell_profit 메서드 업데이트')
else:
    print('Step 2-2 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# 2-3: Update check_tier_cooldown method
old_check_method = '''    @classmethod
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
            return False'''

new_check_method = '''    @classmethod
    def check_tier_cooldown(cls, db: Session, stock_code: str, current_profit_rate: float, portfolio_id: int) -> bool:
        """
        티어 쿨다운 체크 (수익률 상승 기반, DB 조회)
        - 현재 수익률이 마지막 매도 시점보다 높아야 다음 티어 실행 가능
        - Returns: True if next tier is allowed, False otherwise
        """
        try:
            holding = db.query(Holding).filter(
                Holding.portfolio_id == portfolio_id,
                Holding.stock_code == stock_code
            ).first()
            
            # 첫 매도거나 기록 없으면 허용
            if not holding or holding.last_sell_profit is None:
                return True
            
            last_profit = holding.last_sell_profit
            
            # 수익률이 상승했는지 확인 (0.1% 이상 상승해야 함 - 노이즈 방지)
            if current_profit_rate > last_profit + 0.1:
                logger.info(f"[딥바이] {stock_code} 수익률 상승 감지: {last_profit:.2f}% → {current_profit_rate:.2f}%")
                return True
            
            # 수익률이 상승하지 않음
            logger.debug(f"[딥바이] {stock_code} 수익률 미상승: 현재 {current_profit_rate:.2f}% <= 마지막 {last_profit:.2f}%")
            return False
        except Exception as e:
            logger.error(f"[딥바이] {stock_code} 쿨다운 체크 오류: {e}")
            return True  # 오류 시 허용 (안전하게)'''

if old_check_method in content:
    content = content.replace(old_check_method, new_check_method)
    print('Step 2-3 완료: check_tier_cooldown 메서드 업데이트')
else:
    print('Step 2-3 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# 2-4: Update clear_tier_cooldown method
old_clear_method = '''    @classmethod
    def clear_tier_cooldown(cls, stock_code: str):
        """티어 쿨다운 초기화 (장 시작 시 또는 수동 리셋)"""
        with cls._tier_mutex:
            if stock_code in cls._last_sell_profit:
                del cls._last_sell_profit[stock_code]
            logger.info(f"[딥바이] {stock_code} 티어 쿨다운 초기화")'''

new_clear_method = '''    @classmethod
    def clear_tier_cooldown(cls, db: Session, stock_code: str, portfolio_id: int):
        """티어 쿨다운 초기화 (장 시작 시 또는 수동 리셋, DB 업데이트)"""
        try:
            holding = db.query(Holding).filter(
                Holding.portfolio_id == portfolio_id,
                Holding.stock_code == stock_code
            ).first()
            
            if holding and holding.last_sell_profit is not None:
                holding.last_sell_profit = None
                db.commit()
                logger.info(f"[딥바이] {stock_code} 티어 쿨다운 초기화 (DB)")
        except Exception as e:
            logger.error(f"[딥바이] {stock_code} 쿨다운 초기화 오류: {e}")
            db.rollback()'''

if old_clear_method in content:
    content = content.replace(old_clear_method, new_clear_method)
    print('Step 2-4 완료: clear_tier_cooldown 메서드 업데이트')
else:
    print('Step 2-4 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# 2-5: Update get_last_sell_profit method
old_get_method = '''    @classmethod
    def get_last_sell_profit(cls, stock_code: str) -> float:
        """마지막 매도 시 수익률 반환 (없으면 0)"""
        with cls._tier_mutex:
            return cls._last_sell_profit.get(stock_code, 0.0)'''

new_get_method = '''    @classmethod
    def get_last_sell_profit(cls, db: Session, stock_code: str, portfolio_id: int) -> float:
        """마지막 매도 시 수익률 반환 (DB 조회, 없으면 0)"""
        try:
            holding = db.query(Holding).filter(
                Holding.portfolio_id == portfolio_id,
                Holding.stock_code == stock_code
            ).first()
            
            if holding and holding.last_sell_profit is not None:
                return holding.last_sell_profit
            return 0.0
        except Exception as e:
            logger.error(f"[딥바이] {stock_code} 수익률 조회 오류: {e}")
            return 0.0'''

if old_get_method in content:
    content = content.replace(old_get_method, new_get_method)
    print('Step 2-5 완료: get_last_sell_profit 메서드 업데이트')
else:
    print('Step 2-5 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# Write the modified service file
with open(service_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n모든 패치 완료!')
print('다음 단계: DB 마이그레이션 및 check_sell_signal 호출부 수정 필요')

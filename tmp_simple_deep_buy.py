"""
단순 딥바이 전략 v3.6

매수: 현재가 < 평균가 × 0.99 (1% 하락) - 10분 간격
매도: 모드 선택 가능
  - trailing: 고점 대비 분할매도 트레일링 (웹소켓)
  - fixed: 10분 간격 고정 매도 (+2.0%)

[v3.5] 개미떨구기 필터 개선
[v3.6] 전략 모드 스위칭 (API 런타임 변경)
[v4.0] 트레일링 개선: 고점 대비 하락폭 비례 분할매도
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal

logger = logging.getLogger(__name__)

from backend.services.blacklist import is_blacklisted

SellMode = Literal["trailing", "fixed", "virtual"]


class SimpleDeepBuyStrategy:
    """단순 딥바이 전략 with 모드 스위칭"""
    
    # === 공통 설정 ===
    BUY_DROP_PCT = 0.01           # 1% 하락 시 매수 (평단가 기준)
    BUY_DROP_PCT_SELL_REF = 0.015 # 1.5% 하락 시 매수 (매도가 기준)
    CHECK_INTERVAL = 10           # 매수 체크 간격 (분)
    
    # === 트레일링 스톱 설정 (trailing 모드) ===
    TRAILING_TRIGGER = 0.04       # +4.0% 수익 시 트레일링 시작
    
    # === 삼성 종목 최소 보유 설정 ===
    SAMSUNG_CODES = ["005930", "005935", "005380", "066570", "034020"]  # 삼성전자, 삼성전자우, 현대차, LG전자, 두산에너빌리티
    SAMSUNG_MIN_HOLD_QTY = 1  # 최소 1주 보유
    TRAILING_STOP_PCT = 0.015     # (레거시) 고점 대비 -1.5% 하락 시 매도
    TRAILING_SELL_START = 0.005    # 고점 대비 -0.5%부터 매도 시작
    TRAILING_SELL_STEP = 0.005     # -0.5% 간격으로 매도 체크
    SHAKEOUT_WAIT_SEC = 30        # 개미 떨구기 대기 (초)
    SHAKEOUT_MAX_WAIT_SEC = 60    # 최대 대기 (초)
    RECOVERY_THRESHOLD = 0.005    # 회복 기준 (+0.5%)
    
    # 개미떨구기 누적 측정 설정
    SHAKEOUT_CHECK_START = 0.005   # 고점 대비 -0.5%부터 측정 시작
    SHAKEOUT_CHECK_INTERVAL = 0.002  # 0.2% 간격으로 측정 (약 5~6회)
    
    # === 고정 매도 설정 (fixed 모드) ===
    SELL_RISE_PCT = 0.02          # +2.0% 상승 시 매도 (고정매도)
    PEAK_SELL_MIN_PCT = 0.03      # +3.0% 이상에서만 신고가매도
    
    # === 매도가 기준 재매수 설정 ===
    REBUY_FROM_SELL_PCT = 0.03    # 매도가 대비 -3% 하락 시 재매수
    
    def __init__(self):
        self.running = False
        self.kis = None
        
        # 🛑 전종목 매매 정지 (킬스위치)
        self._trading_halted = False
        self._dip_buy_enabled = False  # 낙폭매수(신규종목) ON/OFF — 기본 OFF (재기동 시 신규매수 방지)
        
        # 📉 종목별 직전 매수가 (현재가 < 직전 매수가일 때만 매수)
        self.last_buy_prices: Dict[str, float] = {}
        
        # 🔄 매도 모드 (런타임 변경 가능)
        self._sell_mode: SellMode = "trailing"
        self._mode_lock = threading.Lock()
        
        # 트레일링 상태
        self.trailing_state: Dict[str, Dict] = {}
        
        # 보유 캐시
        self.holdings_cache: Dict[str, Dict] = {}
        
        # 매도 락
        self._sell_lock = threading.Lock()
        self._selling_codes: set = set()
        
        # 매도 대기 목록
        self.pending_sells: Dict[str, Dict] = {}
        
        # 종목별 매도 모드
        self.stock_sell_modes: Dict[str, SellMode] = {}
        
        # 마지막 매도가 추적
        self.last_sell_prices: Dict[str, float] = {}
        self.sell_block_count: Dict[str, int] = {}  # 직전매도 블록 연속 횟수
        
        # [FIX 2026-02-23] 종목별 매도 쿨다운 (연속 매도 방지)
        self._last_sell_time: Dict[str, float] = {}  # stock_code -> timestamp
        self.SELL_COOLDOWN_SEC = self.CHECK_INTERVAL * 60  # 매도 쿨다운(체크 간격과 동일)
        self._load_stock_modes_from_db()
        self._load_last_sell_prices_from_db()
        self._load_last_sell_times_from_db()
        
        # 서버 시작 시 즉시 캐시 초기화 (실시간 콜백 대응)
        self._load_last_buy_prices_from_db()
        self.update_holdings_cache()
        logger.info("[딥바이] 초기 holdings_cache 로드: %d개", len(self.holdings_cache))
    
    # === 모드 관리 API ===
    def get_mode(self, code: str = None) -> SellMode:
        """매도 모드 조회 (종목별 또는 글로벌)"""
        with self._mode_lock:
            if code and code in self.stock_sell_modes:
                return self.stock_sell_modes[code]
            return self._sell_mode
    
    def set_mode(self, mode: SellMode, code: str = None) -> Dict:
        """매도 모드 변경 (글로벌 또는 종목별)"""
        if mode not in ("trailing", "fixed", "virtual"):
            return {"success": False, "error": f"Invalid mode: {mode}. Use 'trailing', 'fixed', or 'virtual'"}
        
        with self._mode_lock:
            if code:
                # 종목별 모드 설정
                old_mode = self.stock_sell_modes.get(code, self._sell_mode)
                self.stock_sell_modes[code] = mode
                logger.info("[딥바이] %s 매도 모드: %s → %s", code, old_mode, mode)
                
                # DB에 저장
                self._save_stock_mode_to_db(code, mode)
                
                return {"success": True, "code": code, "old_mode": old_mode, "new_mode": mode}
            else:
                # 글로벌 모드 변경
                old_mode = self._sell_mode
                self._sell_mode = mode
                
                if mode == "fixed":
                    self.trailing_state.clear()
                    logger.info("[딥바이] 글로벌 모드: %s → %s (트레일링 초기화)", old_mode, mode)
                else:
                    logger.info("[딥바이] 글로벌 모드: %s → %s", old_mode, mode)
                
                return {"success": True, "old_mode": old_mode, "new_mode": mode}
    
    def clear_stock_mode(self, code: str) -> Dict:
        """종목별 모드 삭제 (글로벌 모드 사용)"""
        with self._mode_lock:
            if code in self.stock_sell_modes:
                old_mode = self.stock_sell_modes.pop(code)
                self._save_stock_mode_to_db(code, None)  # DB에서도 삭제
                return {"success": True, "code": code, "removed_mode": old_mode}
            return {"success": False, "message": f"{code} 종목별 모드 없음"}
    
    def get_all_stock_modes(self) -> Dict[str, SellMode]:
        """모든 종목별 모드 조회"""
        with self._mode_lock:
            return self.stock_sell_modes.copy()
    
    def _load_stock_modes_from_db(self):
        """DB에서 종목별 매도 모드 로드"""
        try:
            from backend.database import SessionLocal
            from backend.models.deep_buy_target import DeepBuyTarget
            
            db = SessionLocal()
            try:
                targets = db.query(DeepBuyTarget).filter(
                    DeepBuyTarget.is_active == True,
                    DeepBuyTarget.sell_mode != None
                ).all()
                
                for t in targets:
                    if t.sell_mode in ("trailing", "fixed"):
                        self.stock_sell_modes[t.stock_code] = t.sell_mode
                
                if self.stock_sell_modes:
                    logger.info("[딥바이] DB에서 종목별 모드 로드: %s", self.stock_sell_modes)
            finally:
                db.close()
        except Exception as e:
            logger.warning("[딥바이] 종목별 모드 로드 실패: %s", e)
    
    def _load_last_sell_prices_from_db(self):
        """DB에서 최근 매도가 로드 (마지막 매수 이후 매도가만 참조)"""
        try:
            from backend.database import SessionLocal
            from backend.models.transaction import Transaction
            from backend.models.holding import Holding
            
            db = SessionLocal()
            try:
                # 1. 현재 보유 중인 종목 조회
                holdings = db.query(Holding).filter(Holding.quantity > 0).all()
                held_codes = {h.stock_code for h in holdings}
                
                if not held_codes:
                    logger.info("[딥바이] 보유 종목 없음 - 매도가 로드 스킵")
                    return
                
                # 2. 각 보유 종목의 마지막 매수/매도 비교 후 매도가 로드
                for code in held_codes:
                    last_sell = db.query(Transaction).filter(
                        Transaction.stock_code == code,
                        Transaction.transaction_type == "SELL"
                    ).order_by(Transaction.transaction_date.desc()).first()
                    
                    last_buy = db.query(Transaction).filter(
                        Transaction.stock_code == code,
                        Transaction.transaction_type == "BUY"
                    ).order_by(Transaction.transaction_date.desc()).first()
                    
                    if last_sell:
                        # [FIX 2026-02-26] 매도가는 항상 로드 (추가매수해도 매도 기준 유지)
                        self.last_sell_prices[code] = last_sell.price
                        logger.debug("[딥바이] %s 매도가 로드: %s (체결일: %s)", 
                                    code, last_sell.price, last_sell.transaction_date)
                
                if self.last_sell_prices:
                    logger.info("[딥바이] 매도가 로드 완료: %s", self.last_sell_prices)
                else:
                    logger.info("[딥바이] 매도 기록 없음 (또는 모두 새 포지션)")
            finally:
                db.close()
        except Exception as e:
            logger.warning("[딥바이] 최근 매도가 로드 실패: %s", e)

    def _load_last_sell_times_from_db(self):
        """DB에서 최근 매도 시각 로드 (재시작 직후 연속매도 방지)"""
        try:
            from backend.database import SessionLocal
            from backend.models.transaction import Transaction
            from backend.models.holding import Holding

            db = SessionLocal()
            try:
                holdings = db.query(Holding).filter(Holding.quantity > 0).all()
                held_codes = {h.stock_code for h in holdings}
                if not held_codes:
                    return

                for code in held_codes:
                    last_sell = db.query(Transaction).filter(
                        Transaction.stock_code == code,
                        Transaction.transaction_type == "SELL"
                    ).order_by(Transaction.transaction_date.desc()).first()

                    if last_sell and last_sell.transaction_date:
                        self._last_sell_time[code] = last_sell.transaction_date.timestamp()

                if self._last_sell_time:
                    logger.info("[딥바이] 최근 매도시각 로드 완료: %s", {k:int(v) for k,v in self._last_sell_time.items()})
            finally:
                db.close()
        except Exception as e:
            logger.warning("[딥바이] 최근 매도시각 로드 실패: %s", e)


    def load_all_targets_from_db(self):
        """DB에서 모든 딥바이 대상 종목 로드하여 trailing_state에 추가"""
        try:
            from backend.database import SessionLocal
            from backend.models.deep_buy_target import DeepBuyTarget
            
            db = SessionLocal()
            try:
                targets = db.query(DeepBuyTarget).filter(DeepBuyTarget.is_active == True).all()
                
                for t in targets:
                    code = t.stock_code
                    if code not in self.trailing_state:
                        state = self._create_default_state()
                        # 삼성 종목은 마지막 매도가를 last_peak_sell_price로 설정
                        if code in self.SAMSUNG_CODES and code in self.last_sell_prices:
                            state["last_peak_sell_price"] = self.last_sell_prices[code]
                            logger.info("[딥바이] %s last_peak_sell_price 초기화: %s", 
                                       t.stock_name, format(int(state["last_peak_sell_price"]), ","))
                        self.trailing_state[code] = state
                        logger.info("[딥바이] 타겟 추가: %s (%s)", t.stock_name, code)
                
                logger.info("[딥바이] DB에서 %d개 타겟 로드 완료", len(targets))
            finally:
                db.close()
        except Exception as e:
            logger.warning("[딥바이] 타겟 로드 실패: %s", e)

    def _save_stock_mode_to_db(self, code: str, mode: str):
        """DB에 종목별 매도 모드 저장"""
        try:
            from backend.database import SessionLocal
            from backend.models.deep_buy_target import DeepBuyTarget
            
            db = SessionLocal()
            try:
                target = db.query(DeepBuyTarget).filter(
                    DeepBuyTarget.stock_code == code
                ).first()
                
                if target:
                    target.sell_mode = mode
                    db.commit()
                    logger.info("[딥바이] %s 매도 모드 DB 저장: %s", code, mode)
            finally:
                db.close()
        except Exception as e:
            logger.warning("[딥바이] 종목별 모드 저장 실패: %s", e)
    

    # === 킬스위치 (전종목 매매 정지) ===
    def is_halted(self) -> bool:
        """매매 정지 상태 확인"""
        return self._trading_halted
    
    def halt_trading(self) -> Dict:
        """전종목 매매 정지"""
        self._trading_halted = True
        logger.warning("[킬스위치] 🛑 전종목 매매 정지 활성화")
        return {"success": True, "halted": True, "message": "전종목 매매 정지됨"}
    
    def resume_trading(self) -> Dict:
        """매매 재개"""
        self._trading_halted = False
        logger.info("[킬스위치] ✅ 매매 재개")
        return {"success": True, "halted": False, "message": "매매 재개됨"}
    
    def toggle_halt(self) -> Dict:
        """매매 정지 토글"""
        if self._trading_halted:
            return self.resume_trading()
        else:
            return self.halt_trading()

    def is_dip_buy_enabled(self) -> bool:
        return self._dip_buy_enabled

    def set_dip_buy_enabled(self, enabled: bool):
        self._dip_buy_enabled = enabled
        logger.info("[낙폭매수] %s", "활성화" if enabled else "비활성화")

    def get_status(self) -> Dict:
        """전략 상태 조회"""
        return {
            "running": self.running,
            "sell_mode": self.get_mode(),
            "stock_sell_modes": self.get_all_stock_modes(),
            "holdings_count": len(self.holdings_cache),
            "trading_halted": self._trading_halted,
            "trailing_active_count": sum(1 for s in self.trailing_state.values() if s.get("active")),
            "trailing_state": self.get_trailing_status(),
            "pending_sells_count": len(self.pending_sells),
            "pending_sells": self.get_pending_sells(),
            "settings": {
                "buy_drop_pct": self.BUY_DROP_PCT,
                "trailing_trigger": self.TRAILING_TRIGGER,
                "trailing_stop_pct": self.TRAILING_STOP_PCT,
                "sell_rise_pct": self.SELL_RISE_PCT,
                "check_interval_min": self.CHECK_INTERVAL,
                "rebuy_from_sell_pct": self.REBUY_FROM_SELL_PCT
            },
            "last_sell_prices": self.last_sell_prices

        }
    
    # === 보유 정보 캐시 ===
    def _load_last_buy_prices_from_db(self):
        """DB에서 보유 종목별 직전 매수가 로드"""
        try:
            from backend.database import SessionLocal
            from backend.models.transaction import Transaction
            from backend.models.holding import Holding
            
            db = SessionLocal()
            try:
                holdings = db.query(Holding).filter(Holding.quantity > 0).all()
                held_codes = {h.stock_code for h in holdings}
                
                if not held_codes:
                    return
                
                for code in held_codes:
                    last_buy = db.query(Transaction).filter(
                        Transaction.stock_code == code,
                        Transaction.transaction_type == "BUY"
                    ).order_by(Transaction.transaction_date.desc()).first()
                    
                    if last_buy:
                        self.last_buy_prices[code] = last_buy.price
                        logger.debug("[딥바이] %s 직전 매수가 로드: %s", code, last_buy.price)
                
                if self.last_buy_prices:
                    logger.info("[딥바이] 직전 매수가 로드 완료: %s", 
                               {k: f"{v:,.0f}" for k, v in self.last_buy_prices.items()})
            finally:
                db.close()
        except Exception as e:
            logger.warning("[딥바이] 직전 매수가 로드 실패: %s", e)

    def update_holdings_cache(self):
        """잔고 조회하여 캐시 업데이트"""
        try:
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            balance = self.kis.get_account_balance()
            if not balance:
                return
            
            new_cache = {}
            for holding in balance.get("holdings", []):
                code = holding.get("stock_code", "")
                qty = holding.get("quantity", 0)
                avg_price = float(holding.get("avg_price", 0))
                
                if qty > 0 and avg_price > 0:
                    new_cache[code] = {
                        "qty": qty,
                        "avg_price": avg_price,
                        "name": holding.get("stock_name", code)
                    }
        
            
            self.holdings_cache = new_cache
            
            # 딥바이 대상 종목도 trailing_state에 추가
            self.load_all_targets_from_db()
            
        except Exception as e:
            logger.error("[딥바이v3.6] 보유 캐시 업데이트 실패: %s", e)
    
    # === 실시간 가격 업데이트 (웹소켓) ===
    def on_realtime_price(self, code: str, current_price: float):
        """실시간 가격 콜백 - trailing 모드 종목에서만 동작 (v4: 고점 대비 분할매도)"""
        
        # 🛑 킬스위치 체크
        if self._trading_halted:
            return
        
        # [FIX 2026-02-23] 종목별 모드 체크 (글로벌 모드가 trailing이어도 fixed/virtual 종목은 제외)
        if self.get_mode(code) in ("fixed", "virtual"):
            return
        
        try:
            holding = self.holdings_cache.get(code)
            if not holding:
                return
            
            avg_price = holding["avg_price"]
            qty = holding["qty"]
            name = holding.get("name", code)
            
            if avg_price <= 0 or qty <= 0:
                return
            
            state = self.trailing_state.get(code, self._create_default_state())
            profit_pct = (current_price - avg_price) / avg_price
            
            # 활성화 조건: 수익률 >= TRAILING_TRIGGER
            if profit_pct >= self.TRAILING_TRIGGER:
                if not state["active"]:
                    # 트레일링 활성화
                    state["active"] = True
                    state["peak_price"] = current_price
                    state["last_sold_drop_level"] = 0
                    self.trailing_state[code] = state
                    logger.info("[트레일링v4] 🎯 %s 활성화! 고점=%s (수익 +%.2f%%)", 
                               name, format(int(current_price), ","), profit_pct * 100)
                
                elif current_price > state["peak_price"]:
                    # 고점 갱신 → 매도 레벨 리셋
                    old_peak = state["peak_price"]
                    state["peak_price"] = current_price
                    state["last_sold_drop_level"] = 0
                    self.trailing_state[code] = state
                    if current_price > old_peak * 1.002:  # 0.2% 이상 갱신 시만 로그
                        logger.info("[트레일링v4] 📈 %s 고점 갱신! %s → %s", 
                                   name, format(int(old_peak), ","), format(int(current_price), ","))
                
                else:
                    # [FIX 2026-02-27] 매도 기록 있으면 항상 매도가 기준 (수익/손실 구분 제거)
                    last_sell = self.last_sell_prices.get(code, 0)
                    is_profitable = current_price > avg_price
                    if last_sell > 0:
                        buy_ref_price = last_sell
                        buy_ref_label = "매도가"
                    else:
                        buy_ref_price = avg_price
                        buy_ref_label = "평단가"
                    drop_from_ref = (buy_ref_price - current_price) / buy_ref_price if buy_ref_price > 0 else 0
                    buy_drop_threshold = self.BUY_DROP_PCT_SELL_REF if buy_ref_label == "매도가" else self.BUY_DROP_PCT
                    should_buy = drop_from_ref >= buy_drop_threshold

                    # [FIX 2026-02-27] 매도가 기준 매수 시 갭 체크: 수익 중일 때만 적용
                    # 손실 중(현재가 ≤ 평단가)이면 갭 체크 없이 물타기 허용
                    if should_buy and buy_ref_label == "매도가" and current_price > avg_price:
                        price_gap = (current_price - avg_price) / avg_price if avg_price > 0 else 0
                        if price_gap <= 0.002:
                            should_buy = False

                    # [FIX 2026-02-24] 직전 매수가보다 현재가가 낮을 때만 매수
                    # [FIX 2026-02-25] 직전매수가-평단가 갭 1.5% 초과 시 블록 무시
                    if should_buy:
                        last_buy_price = self.last_buy_prices.get(code, 0)
                        if last_buy_price > 0 and current_price >= last_buy_price:
                            buy_avg_gap = abs(avg_price - last_buy_price) / avg_price if avg_price > 0 else 0
                            if buy_avg_gap > 0.015:
                                logger.info('[트레일링v4] %s 직전매수가-평단가 갭 %.1f%% > 1.5%% → 직전매수 블록 무시', name, buy_avg_gap * 100)
                            else:
                                should_buy = False

                    if should_buy:
                        logger.info("[트레일링v4] %s 매수 조건 충족(%.2f%% 하락) → 트레일링 매도 스킵", name, drop_from_ref * 100)
                    else:
                        # 고점 대비 하락 체크 → 분할매도
                        self._check_trailing_sell(code, name, current_price, avg_price, qty, state)
            
            elif state.get("active") and profit_pct < 0.005:
                # 수익률 0.5% 미만으로 떨어지면 트레일링 비활성화
                state["active"] = False
                state["peak_price"] = 0
                state["last_sold_drop_level"] = 0
                self.trailing_state[code] = state
                logger.info("[트레일링v4] ❌ %s 비활성화 (수익 +%.2f%% < 0.5%%)", name, profit_pct * 100)
                
        except Exception as e:
            logger.error("[트레일링v4] 실시간 가격 처리 오류 (%s): %s", code, e)
    
    def _create_default_state(self) -> Dict:
        return {
            "active": False,
            "peak_price": 0,
            "stop_price": 0,
            "stop_hit_time": None,
            "waiting_for_recovery": False,
            "last_peak_sell_price": 0,  # 마지막 신고가 매도 가격
            "last_sold_drop_level": 0,  # 마지막 매도 발생 하락 레벨
        }
    
    def _check_trailing_sell(self, code: str, name: str, current_price: float,
                            avg_price: float, qty: int, state: dict):
        """고점 대비 하락폭 비례 분할매도 (v4 트레일링)"""
        peak = state.get("peak_price", 0)
        if peak <= 0:
            return
        
        drop_from_peak = (peak - current_price) / peak
        
        if drop_from_peak < self.TRAILING_SELL_START:
            return
        
        # 현재 하락 레벨 (0.5% 단위)
        current_level = int(drop_from_peak / self.TRAILING_SELL_STEP)
        last_level = state.get("last_sold_drop_level", 0)
        
        if current_level <= last_level:
            return  # 이미 이 레벨에서 매도함
        
        # 매도 수량 계산: 하락폭 비례 (고점 대비 -1% → 보유의 10%)
        sell_ratio = min(0.3, drop_from_peak * 10)
        sell_qty = max(1, round(qty * sell_ratio))
        
        # 최소 보유 체크 (삼성 종목)
        if code in self.SAMSUNG_CODES:
            max_sell = qty - self.SAMSUNG_MIN_HOLD_QTY
            if max_sell <= 0:
                logger.info("[트레일링v4] %s 최소 보유 유지 (현재 %d주)", name, qty)
                return
            sell_qty = min(sell_qty, max_sell)
        
        # 수익 체크: 평단 대비 수익이 있을 때만 매도
        profit_pct = (current_price - avg_price) / avg_price
        if profit_pct < 0.005:  # 최소 +0.5% 수익
            logger.info("[트레일링v4] %s 매도 스킵: 수익 +%.2f%% < 0.5%%", name, profit_pct * 100)
            return
        
        logger.info("[트레일링v4] 📉 %s 고점(%s) 대비 -%.1f%% (레벨 %d→%d) → %d주 매도",
                   name, format(int(peak), ","), drop_from_peak * 100,
                   last_level, current_level, sell_qty)
        
        # 매도 실행
        self._execute_trailing_sell(code, name, current_price, avg_price, sell_qty, drop_from_peak)
        
        # 상태 업데이트
        state["last_sold_drop_level"] = current_level
        self.trailing_state[code] = state
    
    def _execute_trailing_sell(self, code: str, name: str, current_price: float,
                               avg_price: float, sell_qty: int, drop_from_peak: float):
        """트레일링 분할매도 실행"""
        try:
            with self._sell_lock:
                if code in self._selling_codes:
                    return
                self._selling_codes.add(code)
            
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            result = self.kis.send_order(code, sell_qty, 0, "1", "01")  # 시장가 매도
            
            if result and result.get("order_no"):
                profit_pct = (current_price - avg_price) / avg_price
                logger.info("[트레일링v4] ✅ %s %d주 매도 완료 (고점 대비 -%.1f%%, 수익 +%.2f%%)",
                           name, sell_qty, drop_from_peak * 100, profit_pct * 100)
                
                self._send_notification_sync(
                    "📉 트레일링 매도: %s %d주 @ %s원 (고점 -%.1f%%, 수익 +%.1f%%)" %
                    (name, sell_qty, format(int(current_price), ","), 
                     drop_from_peak * 100, profit_pct * 100)
                )
                self._save_transaction(code, name, "SELL", sell_qty, current_price, order_no=result.get("order_no"))
                self.last_sell_prices[code] = current_price
                
                # 보유 캐시 업데이트
                if code in self.holdings_cache:
                    self.holdings_cache[code]["qty"] -= sell_qty
                
                # 포트폴리오 업데이트 브로드캐스트
                try:
                    from backend.services.kis_api_service import kis_api_service
                    kis_api_service.broadcast_portfolio_update()
                except Exception:
                    pass
            else:
                logger.warning("[트레일링v4] ❌ %s 매도 실패: %s", name, result)
        except Exception as e:
            logger.error("[트레일링v4] 매도 오류 (%s): %s", name, e)
        finally:
            with self._sell_lock:
                self._selling_codes.discard(code)
    
    def _update_trailing_state(self, code: str, current_price: float, 
                               avg_price: float, name: str, state: dict, qty: int = 0) -> dict:
        """트레일링 상태 업데이트 (레거시 호환용 - v4에서는 on_price_update에서 직접 처리)"""
        profit_pct = (current_price - avg_price) / avg_price
        
        if profit_pct >= self.TRAILING_TRIGGER:
            if not state["active"]:
                state["active"] = True
                state["peak_price"] = current_price
                state["stop_price"] = current_price * (1 - self.TRAILING_STOP_PCT)
                state["last_sold_drop_level"] = 0
                state["name"] = name
            elif current_price > state["peak_price"]:
                state["peak_price"] = current_price
                state["stop_price"] = current_price * (1 - self.TRAILING_STOP_PCT)
                state["last_sold_drop_level"] = 0
        
        self.trailing_state[code] = state
        return state
    
    def _get_shakeout_score(self, code: str, name: str) -> int:
        """개미떨구기 점수 계산 (0~4점)"""
        try:
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            quote = self.kis.get_stock_quote(code)
            if not quote:
                return 0
            
            score = 0
            execution_strength = quote.get("execution_strength", 0)
            buy_vol = quote.get("buy_volume", 0)
            sell_vol = quote.get("sell_volume", 0)
            
            # 체결강도 점수
            if execution_strength >= 100:
                score += 2
            elif execution_strength >= 80:
                score += 1
            
            # 호가잔량 점수
            if buy_vol > 0 and sell_vol > 0:
                ratio = buy_vol / sell_vol
                if ratio >= 1.5:
                    score += 2
                elif ratio >= 1.2:
                    score += 1
            
            return score
        except Exception as e:
            logger.debug(f"[개미떨구기] 점수 계산 실패: {e}")
            return 0


    def _handle_stop_hit(self, code: str, name: str, current_price: float,
                         avg_price: float, qty: int, state: Dict):
        """스톱 도달 처리"""
        with self._sell_lock:
            if code in self._selling_codes:
                return
        
        now = datetime.now()
        profit_pct = (current_price - avg_price) / avg_price
        
        logger.info("[트레일링] 🚨 %s 스톱 도달! 현재가=%s (수익 +%.2f%%)", 
                    name, format(int(current_price), ","), profit_pct * 100)
        
        is_shakeout = self._is_likely_shakeout(code, name)
        
        if is_shakeout:
            state["stop_hit_time"] = now
            state["waiting_for_recovery"] = True
            self.trailing_state[code] = state
            
            logger.info("[트레일링] 🤔 %s 개미 떨구기 추정 → %d초 대기", name, self.SHAKEOUT_WAIT_SEC)
            self._send_notification_sync(
                "🤔 %s 스톱 도달 (수익 +%.1f%%), 외국인 순매수 중 → 회복 대기" % 
                (name, profit_pct * 100)
            )
        else:
            logger.info("[트레일링] 📉 %s 외국인도 매도 중 → 즉시 익절", name)
            self._request_sell(code, name, current_price, avg_price, qty, state, "trailing")
    
    def _check_recovery(self, code: str, name: str, current_price: float,
                        avg_price: float, qty: int, state: Dict):
        """회복 대기 체크"""
        now = datetime.now()
        stop_price = state["stop_price"]
        recovery_price = stop_price * (1 + self.RECOVERY_THRESHOLD)
        
        if current_price >= recovery_price:
            state["waiting_for_recovery"] = False
            state["stop_hit_time"] = None
            state["shakeout_checks"] = []  # 회복 시 누적 측정 초기화
            state["last_check_drop"] = 0
            self.trailing_state[code] = state
            
            profit_pct = (current_price - avg_price) / avg_price
            logger.info("[트레일링] 🎉 %s 가격 회복! → 트레일링 계속", name)
            self._send_notification_sync(
                "🎉 %s 가격 회복! 개미 떨구기였음 → 트레일링 계속 (수익 +%.1f%%)" % 
                (name, profit_pct * 100)
            )
            return
        
        stop_hit_time = state.get("stop_hit_time")
        if stop_hit_time:
            elapsed = (now - stop_hit_time).total_seconds()
            
            if elapsed >= self.SHAKEOUT_MAX_WAIT_SEC:
                logger.info("[트레일링] ⏰ %s 최대 대기 초과 → 익절", name)
                self._request_sell(code, name, current_price, avg_price, qty, state, "trailing")
                return
            
            if elapsed >= self.SHAKEOUT_WAIT_SEC:
                if not self._is_likely_shakeout(code, name):
                    logger.info("[트레일링] 📉 %s 외국인 순매도 전환 → 익절", name)
                    self._request_sell(code, name, current_price, avg_price, qty, state, "trailing")
    
    def _is_likely_shakeout(self, code: str, name: str) -> bool:
        """
        누적 측정 기반 개미 떨구기 판별
        
        - 고점 대비 -0.5%부터 0.2% 간격으로 측정
        - 스톱가 도달 시 누적 평균 점수로 판단
        - 평균 점수 >= 1.5 → 개미떨구기
        """
        state = self.trailing_state.get(code, {})
        checks = state.get("shakeout_checks", [])
        
        if not checks:
            # 측정 기록 없으면 즉시 측정
            score = self._get_shakeout_score(code, name)
            is_shakeout = score >= 2
            logger.info(f"[개미떨구기] {name} 즉시 측정: 점수 {score}/4 → {'개미떨구기' if is_shakeout else '진짜하락'}")
            return is_shakeout
        
        # 누적 평균 점수 계산
        avg_score = sum(c["score"] for c in checks) / len(checks)
        max_score = max(c["score"] for c in checks)
        
        # 판단 기준: 평균 >= 1.5 또는 최대 >= 3
        is_shakeout = avg_score >= 1.5 or max_score >= 3
        
        logger.warning(
            f"[개미떨구기] {'⚠️' if is_shakeout else '📉'} {name} 누적 판단: "
            f"{len(checks)}회 측정, 평균 {avg_score:.1f}, 최대 {max_score} → "
            f"{'개미떨구기 의심!' if is_shakeout else '진짜 하락'}"
        )
        
        return is_shakeout
    async def _check_fixed_sell(self, code: str, name: str, current_price: float,
                                 avg_price: float, qty: int) -> int:
        """고정 간격 매도 체크 (+2.0%, 기준가 = 평단가 + 직전매도가 필터). Returns: 실제 매도된 수량"""
        profit_pct = (current_price - avg_price) / avg_price

        # [FIX 2026-02-26] 직전매도 블록 3연속 시 해제 (래칫 방지)
        last_sell_price = self.last_sell_prices.get(code, 0)

        if profit_pct >= self.SELL_RISE_PCT:
            if last_sell_price > 0 and current_price <= last_sell_price:
                self.sell_block_count[code] = self.sell_block_count.get(code, 0) + 1
                block_cnt = self.sell_block_count[code]
                if block_cnt >= 3:
                    # 3연속 블록 -> 직전매도가 해제
                    logger.info(
                        "[고정매도] %s: 직전매도 블록 %d연속 -> 직전매도가(%s) 해제!",
                        name, block_cnt, format(int(last_sell_price), ","))
                    del self.last_sell_prices[code]
                    self.sell_block_count[code] = 0
                    last_sell_price = 0
                    # 해제 후 매도 진행 (아래 로직으로 fall through)
                else:
                    logger.info(
                        "[고정매도] %s: 조건 충족(+%.2f%%)이지만 현재가(%s) <= 직전매도가(%s) -> 매도 보류 (%d/3)",
                        name, profit_pct * 100,
                        format(int(current_price), ","),
                        format(int(last_sell_price), ","),
                        block_cnt)
                    return 0

            sell_qty = self._calc_quantity(qty, profit_pct, is_sell=True)
            if sell_qty <= 0:
                sell_qty = 1  # 최소 1주 매도

            logger.info("[고정매도] %s: 평단가(%s) 기준 +%.2f%% ≥ +%.1f%% → 매도 %d주",
                        name, format(int(avg_price), ","),
                        profit_pct * 100, self.SELL_RISE_PCT * 100, sell_qty)

            sold = await self._execute_sell_async(code, name, current_price, avg_price, sell_qty, "fixed")
            if sold:
                self.sell_block_count[code] = 0  # 매도 성공 시 블록 카운트 리셋
            return sold if sold else 0
        return 0
    
    def _check_virtual_sell(self, code: str, name: str, current_price: float,
                              avg_price: float, qty: int) -> int:
        """가상매도: 실제 매도 없이 매도가만 갱신 (virtual 모드)"""
        profit_pct = (current_price - avg_price) / avg_price

        last_sell_price = self.last_sell_prices.get(code, 0)

        if profit_pct >= self.SELL_RISE_PCT:
            if last_sell_price > 0 and current_price <= last_sell_price:
                self.sell_block_count[code] = self.sell_block_count.get(code, 0) + 1
                block_cnt = self.sell_block_count[code]
                if block_cnt >= 3:
                    logger.info("[가상매도] %s: 직전매도 블록 %d연속 -> 직전매도가(%s) 해제!",
                        name, block_cnt, format(int(last_sell_price), ","))
                    del self.last_sell_prices[code]
                    self.sell_block_count[code] = 0
                    last_sell_price = 0
                else:
                    logger.info("[가상매도] %s: 조건(+%.2f%%) 충족이나 현재가(%s) <= 직전매도가(%s) -> 보류 (%d/3)",
                        name, profit_pct * 100, format(int(current_price), ","),
                        format(int(last_sell_price), ","), block_cnt)
                    return 0

            # 가상매도: 실제 주문 없이 매도가만 갱신
            self.last_sell_prices[code] = current_price
            self.sell_block_count[code] = 0

            import time as _time
            self._last_sell_time[code] = _time.time()

            logger.info("[가상매도] 👻 %s: +%.2f%% @ %s원 → 매도가 갱신 (실제 매도 없음)",
                        name, profit_pct * 100, format(int(current_price), ","))

            # 신고가 기준도 동기화
            if code in self.trailing_state:
                prev_peak_sell = self.trailing_state[code].get("last_peak_sell_price", 0)
                self.trailing_state[code]["last_peak_sell_price"] = max(prev_peak_sell, current_price)

            return 1  # 가상이지만 1주 매도 취급 (신고가매도 중복 방지)
        return 0

        # === 매도 실행 ===
    def _request_sell(self, code: str, name: str, current_price: float,
                      avg_price: float, qty: int, state: Dict, mode: str):
        """매도 신호 발송 및 대기 등록 (실제 매도 X)"""
        profit_pct = (current_price - avg_price) / avg_price
        
        # 매도 대기 등록
        self.pending_sells[code] = {
            "code": code,
            "name": name,
            "current_price": current_price,
            "avg_price": avg_price,
            "quantity": qty,
            "profit_pct": profit_pct,
            "mode": mode,
            "state": state.copy(),
            "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # 텔레그램 알림
        mode_emoji = "📉" if mode == "trailing" else "💰"
        msg = (
            f"{mode_emoji} 매도 신호: {name}\n"
            f"• 현재가: {current_price:,}원\n"
            f"• 평균가: {avg_price:,}원\n"
            f"• 수익률: +{profit_pct*100:.1f}%\n"
            f"• 수량: {qty}주\n"
            f"• 예상 금액: {int(current_price * qty):,}원\n\n"
            f"💬 '매도해줘' 또는 '{name} 매도' 라고 하시면 실행합니다."
        )
        
        self._send_notification_sync(msg)
        logger.info("[매도대기] %s 매도 신호 발송 (수익 +%.1f%%)", name, profit_pct * 100)
    
    def confirm_sell(self, code: str = None, name: str = None) -> Dict:
        """매도 확인 (텔레그램에서 호출)"""
        # code 또는 name으로 찾기
        target = None
        if code and code in self.pending_sells:
            target = code
        elif name:
            for c, info in self.pending_sells.items():
                if name in info["name"]:
                    target = c
                    break
        
        # 없으면 첫 번째 대기 종목
        if not target and self.pending_sells:
            target = list(self.pending_sells.keys())[0]
        
        if not target:
            return {"success": False, "message": "매도 대기 중인 종목이 없습니다."}
        
        info = self.pending_sells[target]
        
        try:
            # 실제 매도 실행
            result = self._do_sell(
                info["code"], info["name"], info["current_price"],
                info["avg_price"], info["quantity"], info["state"], info["mode"]
            )
            
            # 대기 목록에서 제거
            del self.pending_sells[target]
            
            return {"success": True, "message": f"{info['name']} 매도 완료!", "result": result}
            
        except Exception as e:
            logger.error(f"매도 실행 실패: {e}")
            return {"success": False, "message": f"매도 실패: {e}"}
    
    def cancel_sell(self, code: str = None, name: str = None) -> Dict:
        """매도 취소"""
        target = None
        if code and code in self.pending_sells:
            target = code
        elif name:
            for c, info in self.pending_sells.items():
                if name in info["name"]:
                    target = c
                    break
        
        if not target:
            return {"success": False, "message": "매도 대기 중인 종목이 없습니다."}
        
        info = self.pending_sells[target]
        del self.pending_sells[target]
        
        return {"success": True, "message": f"{info['name']} 매도 취소됨"}
    
    def get_pending_sells(self) -> list:
        """대기 중인 매도 목록"""
        return list(self.pending_sells.values())
    
    def _do_sell(self, code: str, name: str, current_price: float,
                 avg_price: float, qty: int, state: Dict, mode: str):
        """실제 매도 실행 (내부용)"""
        profit_pct = (current_price - avg_price) / avg_price
        
        # 티어 매도 수량 계산
        if mode == "trailing" and state.get("peak_price"):
            peak_profit_pct = (state["peak_price"] - avg_price) / avg_price
            sell_qty = self._calc_quantity(qty, peak_profit_pct, is_sell=True)
        else:
            sell_qty = self._calc_quantity(qty, profit_pct, is_sell=True)
        
        if sell_qty <= 0:
                            sell_qty = 1  # 최소 1주 매도
        
        # 삼성 최소 보유 체크 (최소 1주 유지)
        if code in self.SAMSUNG_CODES:
            remaining = qty - sell_qty
            if remaining < self.SAMSUNG_MIN_HOLD_QTY:
                max_sell = qty - self.SAMSUNG_MIN_HOLD_QTY
                if max_sell <= 0:
                    self._send_notification_sync(
                        f"⚠️ {name} 매도 스킵: 최소 {self.SAMSUNG_MIN_HOLD_QTY}주 보유 유지"
                    )
                    return {"success": False, "message": "삼성 최소 보유"}
                sell_qty = max_sell
                logger.info(f"[딥바이] {name} 최소 보유 적용: {sell_qty}주만 매도 (1주 유지)")
        
        # 실제 매도 주문
        if self.kis:
            result = self.kis.sell_stock(code, sell_qty, 0)
            
            if result and result.get("success"):
                mode_emoji = "📉" if mode == "trailing" else "💰"
                mode_text = "트레일링" if mode == "trailing" else "고정"
                
                self._send_notification_sync(
                    f"{mode_emoji} {name} {mode_text} 매도 완료!\n"
                    f"• {sell_qty}주 × {current_price:,}원\n"
                    f"• 수익률: +{profit_pct*100:.1f}%"
                )
                
                # 트레일링 상태 초기화
                if mode == "trailing":
                    self.trailing_state[code] = self._create_default_state()
                
                return {"success": True, "quantity": sell_qty}
        
        return {"success": False, "message": "KIS API 없음"}

    def _execute_sell(self, code: str, name: str, current_price: float,
                       avg_price: float, qty: int, state: Dict, mode: str):
        """동기 매도 (트레일링용)"""
        with self._sell_lock:
            if code in self._selling_codes:
                return
            self._selling_codes.add(code)
        
        try:
            profit_pct = (current_price - avg_price) / avg_price
            
            if mode == "trailing" and state.get("peak_price"):
                peak_profit_pct = (state["peak_price"] - avg_price) / avg_price
                sell_qty = self._calc_quantity(qty, peak_profit_pct, is_sell=True)
            else:
                sell_qty = self._calc_quantity(qty, profit_pct, is_sell=True)
            
            if sell_qty <= 0:
                            sell_qty = 1  # 최소 1주 매도
            sell_qty = min(sell_qty, qty)
            
            # 삼성전자/삼성전자우: 총자산의 10%는 유지
            if code in self.SAMSUNG_CODES:
                # 최소 1주 보유
                max_sell_qty = qty - self.SAMSUNG_MIN_HOLD_QTY
                if sell_qty > max_sell_qty:
                    logger.info("[딥바이v3.6] %s 최소 %d주 유지", name, self.SAMSUNG_MIN_HOLD_QTY)
                    sell_qty = max_sell_qty
                if sell_qty <= 0:
                    return
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            # 삼성전자/삼성전자우: 총자산의 10%는 유지
            if code in self.SAMSUNG_CODES:
                try:
                    balance = self.kis.get_account_balance() if self.kis else None
                    if balance and balance.get("total_asset"):
                        total_asset = balance["total_asset"]
                        min_hold_qty = self.SAMSUNG_MIN_HOLD_QTY

                        # 수량 기반 최소 보유 체크 (실제 보유량 기준)
                        holding_qty = self.holdings_cache.get(code, {}).get("qty", 0)
                        if holding_qty <= 0:
                            for h in balance.get("holdings", []):
                                if h.get("stock_code") == code:
                                    holding_qty = h.get("quantity", 0)
                                    break
                        remaining_qty = holding_qty - sell_qty
                        if remaining_qty < min_hold_qty:
                            max_sell_qty = holding_qty - min_hold_qty
                            if max_sell_qty <= 0:
                                logger.info("[딥바이v3.6] ⚠️ %s 매도 스킵: 최소 %d주 보유 (보유 %d주)", name, min_hold_qty, holding_qty)
                                return
                            sell_qty = max_sell_qty
                            logger.info("[딥바이v3.6] %s 매도 수량 조정: %d주 (보유 %d주, 최소 %d주 유지)", name, sell_qty, holding_qty, min_hold_qty)
                except Exception as e:
                    logger.warning("[딥바이v3.6] 10%% 체크 오류: %s", e)
            
            result = self.kis.send_order(code, sell_qty, 0, "1", "01")
            
            if result and result.get("order_no"):
                logger.info("[딥바이v3.6] ✅ %s 매도 완료: %d주, 수익 +%.2f%%", 
                            name, sell_qty, profit_pct * 100)
                
                mode_emoji = "📉" if mode == "trailing" else "💰"
                mode_text = "트레일링" if mode == "trailing" else "고정"
                
                self._send_notification_sync(
                    "%s %s 익절: %s %d주 @ %s원 (수익 +%.1f%%)" % 
                    (mode_emoji, mode_text, name, sell_qty, 
                     format(int(current_price), ","), profit_pct * 100)
                )
                self._save_transaction(code, name, "SELL", sell_qty, current_price, order_no=result.get("order_no"))
                self.last_sell_prices[code] = current_price  # 매도가 저장
                logger.info("[딥바이v3.6] 📝 %s 매도가 저장: %s원", name, format(int(current_price), ","))

                # [FIX 2026-02-25] 고정매도/트레일링매도 후 신고가 기준도 동기화
                if code in self.trailing_state:
                    prev_peak_sell = self.trailing_state[code].get("last_peak_sell_price", 0)
                    self.trailing_state[code]["last_peak_sell_price"] = max(prev_peak_sell, current_price)
                
                if code in self.holdings_cache:
                    self.holdings_cache[code]["qty"] -= sell_qty
                    if self.holdings_cache[code]["qty"] <= 0:
                        del self.holdings_cache[code]
            
            # 트레일링 상태 초기화
            if mode == "trailing":
                self.trailing_state[code] = self._create_default_state()
            
        except Exception as e:
            logger.error("[딥바이v3.6] 매도 오류 (%s): %s", name, e)
        finally:
            with self._sell_lock:
                self._selling_codes.discard(code)
    
    async def _execute_sell_async(self, code: str, name: str, current_price: float,
                                   avg_price: float, qty: int, mode: str):
        """비동기 매도 (고정 간격용)"""
        with self._sell_lock:
            if code in self._selling_codes:
                return
            self._selling_codes.add(code)
        
        try:
            profit_pct = (current_price - avg_price) / avg_price
            sell_qty = qty  # qty는 이미 계산된 매도 수량
            if sell_qty <= 0:
                            sell_qty = 1  # 최소 1주 매도
            
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            # 삼성전자/삼성전자우: 총자산의 10%는 유지
            if code in self.SAMSUNG_CODES:
                try:
                    balance = self.kis.get_account_balance() if self.kis else None
                    if balance and balance.get("total_asset"):
                        total_asset = balance["total_asset"]
                        min_hold_qty = self.SAMSUNG_MIN_HOLD_QTY

                        # 수량 기반 최소 보유 체크 (실제 보유량 기준)
                        holding_qty = self.holdings_cache.get(code, {}).get("qty", 0)
                        if holding_qty <= 0:
                            for h in balance.get("holdings", []):
                                if h.get("stock_code") == code:
                                    holding_qty = h.get("quantity", 0)
                                    break
                        remaining_qty = holding_qty - sell_qty
                        if remaining_qty < min_hold_qty:
                            max_sell_qty = holding_qty - min_hold_qty
                            if max_sell_qty <= 0:
                                logger.info("[딥바이v3.6] ⚠️ %s 매도 스킵: 최소 %d주 보유 (보유 %d주)", name, min_hold_qty, holding_qty)
                                return
                            sell_qty = max_sell_qty
                            logger.info("[딥바이v3.6] %s 매도 수량 조정: %d주 (보유 %d주, 최소 %d주 유지)", name, sell_qty, holding_qty, min_hold_qty)
                except Exception as e:
                    logger.warning("[딥바이v3.6] 10%% 체크 오류: %s", e)
            
            result = self.kis.send_order(code, sell_qty, 0, "1", "01")
            
            if result and result.get("order_no"):
                logger.info("[딥바이v3.6] ✅ %s 고정매도 완료: %d주", name, sell_qty)
                await self._send_notification(
                    "💰 고정 익절: %s %d주 @ %s원 (수익 +%.1f%%)" % 
                    (name, sell_qty, format(int(current_price), ","), profit_pct * 100)
                )
                self._save_transaction(code, name, "SELL", sell_qty, current_price, order_no=result.get("order_no"))
                self.last_sell_prices[code] = current_price  # 매도가 저장
                logger.info("[딥바이v3.6] 📝 %s 매도가 저장: %s원", name, format(int(current_price), ","))

                # [FIX 2026-02-25] 고정매도 후 신고가 기준도 동기화
                if code in self.trailing_state:
                    prev_peak_sell = self.trailing_state[code].get("last_peak_sell_price", 0)
                    self.trailing_state[code]["last_peak_sell_price"] = max(prev_peak_sell, current_price)
                
                # [FIX 2026-02-23] 매도 쿨다운 타임스탬프 기록
                import time as _time
                self._last_sell_time[code] = _time.time()
                
                self.update_holdings_cache()
                await self._broadcast_holdings_update()
                return sell_qty
            return 0
                
        except Exception as e:
            logger.error("[딥바이v3.6] 매도 오류: %s", e)
            return 0
        finally:
            with self._sell_lock:
                self._selling_codes.discard(code)
    

    def _get_samsung_holdings(self) -> list:
        """삼성전자/삼성전자우 보유 정보 가져오기"""
        try:
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            balance = self.kis.get_account_balance()
            if balance and balance.get("holdings"):
                return [h for h in balance["holdings"] if h.get("pdno") in self.SAMSUNG_CODES]
        except Exception as e:
            logger.warning("[딥바이v3.6] 삼성 보유 조회 오류: %s", e)
        return []
    
    def _get_total_assets(self) -> float:
        """총자산 조회"""
        try:
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            balance = self.kis.get_account_balance()
            if balance:
                return balance.get("total_asset", 0)
        except Exception as e:
            logger.warning("[딥바이v3.6] 총자산 조회 오류: %s", e)
        return 0

    def _calc_quantity(self, holding_qty: int, profit_pct: float, is_sell: bool = False) -> int:
        """매수/매도 수량 계산 (보유수량 비례, 낙폭에 따라 10~30%)
        
        -1% → 보유수량의 10%
        -2% → 보유수량의 20%
        -3%+ → 보유수량의 30%
        최소 1주 보장
        [FIX 2026-02-26] 매도 시 보유 30주 이하면 무조건 1주
        """
        # 매도 시 보유 30주 이하면 무조건 1주만
        if is_sell and holding_qty <= 30:
            return 1
        abs_pct = abs(profit_pct * 100)  # ex: 0.01 → 1.0
        ratio = min(0.3, max(0.1, abs_pct * 0.1))  # 10%~30%
        qty = round(holding_qty * ratio)
        return max(1, qty)
    
    # === 알림 ===
    def _send_notification_sync(self, message: str):
        try:
            import asyncio
            from backend.services.telegram_service import TelegramService
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    TelegramService.send_message("[딥바이v3.6] " + message)
                )
            finally:
                loop.close()
        except Exception as e:
            logger.warning("[딥바이v3.6] 알림 실패: %s", e)
    
    async def _send_notification(self, message: str):
        try:
            from backend.services.telegram_service import TelegramService
            await TelegramService.send_message("[딥바이v3.6] " + message)
        except Exception as e:
            logger.warning("[딥바이v3.6] 알림 실패: %s", e)
    
    async def _broadcast_holdings_update(self):
        """잔고 변경 WebSocket 브로드캐스트"""
        try:
            from backend.main import broadcast_portfolio_update
            await broadcast_portfolio_update()
            logger.info("[딥바이v3.6] 📡 잔고 변경 브로드캐스트 전송")
        except Exception as e:
            logger.warning("[딥바이v3.6] 브로드캐스트 실패: %s", e)
    
    # === 메인 루프 ===
    async def start(self):
        """스케줄러 시작"""
        from backend.services.kis_api_service import kis_api_service
        self.kis = kis_api_service
        self.running = True
        
        mode = self.get_mode()
        logger.info("[딥바이v3.6] 시작 - 매도 모드: %s", mode)
        logger.info("  매수: 평균가 대비 -%s%% (10분 간격)", self.BUY_DROP_PCT*100)
        if mode == "trailing":
            logger.info("  매도: 트레일링 스톱 (실시간)")
        else:
            logger.info("  매도: 고정 +%s%% (10분 간격)", self.SELL_RISE_PCT*100)
        
        self.update_holdings_cache()
        
        while self.running:
            try:
                now = datetime.now()
                
                if not self._is_market_hours(now):
                    await asyncio.sleep(60)
                    continue
                
                if now.minute % self.CHECK_INTERVAL == 0 and now.second < 5:
                    self.update_holdings_cache()
                    await self._run_cycle(now)
                    await asyncio.sleep(60)
                else:
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error("[딥바이v3.6] 오류: %s", e)
                await asyncio.sleep(30)
    
    def stop(self):
        self.running = False
        logger.info("[딥바이v3.6] 중지")
    
    async def _run_cycle(self, now: datetime):
        """매수 + (fixed 모드일 때) 매도 사이클"""
        # 🛑 킬스위치 체크
        if self._trading_halted:
            logger.warning("[킬스위치] 🛑 매매 정지 중 - 사이클 스킵")
            return
        
        time_str = now.strftime("%H:%M")
        mode = self.get_mode()
        logger.info("[딥바이v3.6] === 사이클 실행 (%s, 모드: %s) ===", time_str, mode)
        
        balance = self.kis.get_account_balance()
        if not balance:
            return
        
        cash = balance.get("orderable_cash", 0)
        
        for holding in balance.get("holdings", []):
            code = holding.get("stock_code", "")
            name = holding.get("stock_name", code)
            qty = holding.get("quantity", 0)
            avg_price = float(holding.get("avg_price", 0))
            
            if qty <= 0 or avg_price <= 0:
                continue
            
            quote = self.kis.get_stock_quote(code)
            if not quote:
                continue
            
            current_price = float(quote.get("current_price", 0))
            if current_price <= 0:
                continue
            
            profit_pct = (current_price - avg_price) / avg_price
            
            logger.info("[딥바이v3.6] %s: 현재가=%s, 평균가=%s, 수익률=%.2f%%",
                        name, format(int(current_price), ","), 
                        format(int(avg_price), ","), profit_pct * 100)
            
            # 블랙리스트 체크
            if is_blacklisted(code):
                logger.debug('[딥바이] %s 블랙리스트 → 매수 스킵', name)
                continue

            # 매수 조건 먼저 판단 (매수 우선 정책)
            # [FIX 2026-02-27] 매도 기록 있으면 항상 매도가 기준 (수익/손실 구분 제거)
            last_sell = self.last_sell_prices.get(code, 0)
            is_profitable = current_price > avg_price
            if last_sell > 0:
                buy_ref_price = last_sell
                buy_ref_label = "매도가"
            else:
                buy_ref_price = avg_price
                buy_ref_label = "평단가"
            drop_from_ref = (buy_ref_price - current_price) / buy_ref_price if buy_ref_price > 0 else 0
            buy_drop_threshold = self.BUY_DROP_PCT_SELL_REF if buy_ref_label == "매도가" else self.BUY_DROP_PCT
            should_buy = drop_from_ref >= buy_drop_threshold
            # [FIX 2026-02-27] 매도가 기준 매수 시 갭 체크: 수익 중일 때만 적용
            # 손실 중(현재가 ≤ 평단가)이면 갭 체크 없이 물타기 허용
            if should_buy and buy_ref_label == "매도가" and current_price > avg_price:
                price_gap = (current_price - avg_price) / avg_price if avg_price > 0 else 0
                if price_gap <= 0.002:
                    logger.info("[딥바이v3.6] %s 수익 중 매도가 기준 매수이나 현재가-평단가 갭 %.3f%% ≤ 0.2%% → 매수 스킵", name, price_gap * 100)
                    should_buy = False

            # [FIX 2026-02-24] 직전 매수가보다 현재가가 낮을 때만 매수
            # [FIX 2026-02-25] 직전매수가-평단가 갭 1.5% 초과 시 블록 무시
            # [FIX 2026-02-26] 매도가 기준 매수 시 직전매수 블록 무시
            if should_buy and buy_ref_label == "평단가":
                last_buy_price = self.last_buy_prices.get(code, 0)
                if last_buy_price > 0 and current_price >= last_buy_price:
                    buy_avg_gap = abs(avg_price - last_buy_price) / avg_price if avg_price > 0 else 0
                    if buy_avg_gap > 0.015:
                        logger.info("[딥바이v3.6] %s 직전매수가(%s)-평단가(%s) 갭 %.1f%% > 1.5%% → 직전매수 블록 무시",
                                   name, format(int(last_buy_price), ","), format(int(avg_price), ","), buy_avg_gap * 100)
                    else:
                        logger.info("[딥바이v3.6] %s 현재가(%s) ≥ 직전매수가(%s) → 매수 스킵",
                                   name, format(int(current_price), ","), format(int(last_buy_price), ","))
                        should_buy = False

            if should_buy:
                logger.info("[딥바이v3.6] %s 매수 조건 충족 → 매도 스킵 (매수 우선)", name)
            else:
                sold_in_cycle = 0
                
                # [FIX 2026-02-23] 종목별 매도 쿨다운 체크 (연속 매도 방지)
                import time as _time
                _last_sell = self._last_sell_time.get(code, 0)
                if _time.time() - _last_sell < self.SELL_COOLDOWN_SEC:
                    _remaining = int(self.SELL_COOLDOWN_SEC - (_time.time() - _last_sell))
                    logger.info("[딥바이v3.6] %s 매도 쿨다운 중 (%d초 남음) → 매도 스킵", name, _remaining)
                    continue
                
                # 매도 체크 (fixed/virtual 모드)
                effective_mode = self.get_mode(code)
                if effective_mode == "fixed":
                    sold_in_cycle = await self._check_fixed_sell(code, name, current_price, avg_price, qty)
                elif effective_mode == "virtual":
                    sold_in_cycle = self._check_virtual_sell(code, name, current_price, avg_price, qty)
                
                # 삼성 종목 신고가 체크 (10분 단위, fixed 모드만) — 고정매도 후 남은 수량 반영
                adjusted_qty = qty - sold_in_cycle
                # [FIX 2026-02-23] 같은 사이클에서 고정매도 후 신고가매도 연속 실행 금지
                if sold_in_cycle > 0:
                    logger.info("[딥바이v3.6] %s 고정매도 실행됨(%d주) → 같은 사이클 신고가매도 스킵", name, sold_in_cycle)
                if code in self.SAMSUNG_CODES and adjusted_qty > 0 and sold_in_cycle == 0 and self.get_mode(code) in ("fixed", "virtual"):
                    state = self.trailing_state.get(code, {})
                    last_peak_sell = state.get("last_peak_sell_price", 0)
                    last_sell_price = self.last_sell_prices.get(code, 0)
                    peak_ref_price = max(last_peak_sell, last_sell_price)
                    if current_price > peak_ref_price:
                        logger.info("[신고가매도] %s 신고가 갱신! 현재가=%s > 기준가=%s (이전고점=%s, 직전매도가=%s, 잔여 %d주)",
                                   name,
                                   format(int(current_price), ","),
                                   format(int(peak_ref_price), ","),
                                   format(int(last_peak_sell), ","),
                                   format(int(last_sell_price), ","),
                                   adjusted_qty)
                        self._sell_one_share_on_peak(code, name, current_price, avg_price, adjusted_qty)
                        if code in self.trailing_state:
                            self.trailing_state[code]["last_peak_sell_price"] = current_price


            # trailing 모드 10분 주기 백업 체크 (WebSocket 미연결 시 대비)
            if not should_buy and self.get_mode(code) == "trailing":
                state = self.trailing_state.get(code, {})
                if state.get("active") and state.get("peak_price", 0) > 0:
                    self._check_trailing_sell(code, name, current_price, avg_price, qty, state)

            # 매수 실행
            if should_buy:
                # [FIX 2026-02-27] 수량 계산은 평단가 대비 낙폭 기준 (매도가 대비 과다매수 방지)
                drop_for_qty = max(0, (avg_price - current_price) / avg_price) if avg_price > 0 else 0
                buy_qty = self._calc_quantity(qty, drop_for_qty)
                # [FIX 2026-02-26] 수익 중 매수량 50% 축소
                if is_profitable:
                    buy_qty = max(1, round(buy_qty * 0.5))
                if buy_qty > 0:
                    buy_reason = "%s(%s) 대비 -%.1f%%, 평단 대비 -%.1f%%" % (
                        buy_ref_label,
                        format(int(buy_ref_price), ","),
                        drop_from_ref * 100,
                        drop_for_qty * 100,
                    )
                    required_cash = current_price * buy_qty * 1.001
                    if cash >= required_cash:
                        await self._execute_buy(code, name, current_price, buy_qty, buy_reason)
                        cash -= required_cash
                    else:
                        # [NEW] 자금 부족 시 1주 fallback (자동매매)
                        fallback_qty = 1
                        fallback_cash = current_price * fallback_qty * 1.001
                        if buy_qty > 1 and cash >= fallback_cash:
                            logger.warning(
                                "[딥바이v3.6] %s 자금 부족 (필요: %s원, 가용: %s원, %d주) → 1주 fallback 시도",
                                name,
                                format(int(required_cash), ","),
                                format(int(cash), ","),
                                buy_qty,
                            )
                            await self._execute_buy(
                                code,
                                name,
                                current_price,
                                fallback_qty,
                                f"{buy_reason}, 자금부족 1주 fallback",
                            )
                            cash -= fallback_cash
                        else:
                            logger.warning(
                                "[딥바이v3.6] %s 자금 부족 (필요: %s원, 가용: %s원, %d주)",
                                name,
                                format(int(required_cash), ","),
                                format(int(cash), ","),
                                buy_qty,
                            )
    async def _execute_buy(self, code: str, name: str, price: float, qty: int, reason: str = ""):
        logger.info("[딥바이v3.6] 📈 매수: %s %d주 @ %s", name, qty, format(int(price), ","))

        try:
            result = self.kis.send_order(code, qty, 0, "2", "01")
            if result and result.get("order_no"):
                self.last_buy_prices[code] = price  # 직전 매수가 업데이트
                await self._send_notification("📈 매수: %s %d주 @ %s원 (%s)" % (name, qty, format(int(price), ","), reason if reason else "추가매수"))
                self._save_transaction(code, name, "BUY", qty, price, order_no=result.get("order_no"))
                self.update_holdings_cache()
                await self._broadcast_holdings_update()
                return

            logger.error("[딥바이v3.6] 매수 오류: 주문 응답 없음 (%s, %d주)", name, qty)

        except Exception as e:
            err_msg = str(e)
            is_insufficient_cash = ("주문가능금액" in err_msg and "초과" in err_msg)

            # [NEW] 주문 API에서 자금 부족 발생 시 1주 fallback 재시도
            if is_insufficient_cash and qty > 1:
                logger.warning("[딥바이v3.6] %s 주문가능금액 부족으로 1주 fallback 재시도 (%d주→1주)", name, qty)
                try:
                    fallback_qty = 1
                    fallback_result = self.kis.send_order(code, fallback_qty, 0, "2", "01")
                    if fallback_result and fallback_result.get("order_no"):
                        self.last_buy_prices[code] = price
                        await self._send_notification(
                            "📈 매수: %s %d주 @ %s원 (%s, 1주 fallback)" % (
                                name,
                                fallback_qty,
                                format(int(price), ","),
                                reason if reason else "추가매수",
                            )
                        )
                        self._save_transaction(code, name, "BUY", fallback_qty, price, order_no=fallback_result.get("order_no"))
                        self.update_holdings_cache()
                        await self._broadcast_holdings_update()
                        logger.info("[딥바이v3.6] %s 1주 fallback 매수 성공", name)
                        return
                except Exception as fallback_e:
                    logger.error("[딥바이v3.6] %s 1주 fallback 매수 실패: %s", name, fallback_e)

            logger.error("[딥바이v3.6] 매수 오류: %s", e)
    
    def _save_transaction(self, code: str, name: str, tx_type: str, qty: int, price: float, order_no: str = None):
        try:
            from backend.database import SessionLocal
            from backend.models.transaction import Transaction
            from backend.models.holding import Holding
            from backend.services.real_account_service import RealAccountService
            from datetime import timedelta
            
            db = SessionLocal()
            try:
                portfolio = RealAccountService.get_or_create_real_portfolio(db)

                # [FIX] 중복 방지: 같은 종목/타입/수량/근접시간(3초) 거래가 있으면 스킵
                now = datetime.now()
                dup = db.query(Transaction).filter(
                    Transaction.portfolio_id == portfolio.id,
                    Transaction.stock_code == code,
                    Transaction.transaction_type == tx_type,
                    Transaction.quantity == qty,
                    Transaction.transaction_date >= now - timedelta(seconds=3)
                ).order_by(Transaction.transaction_date.desc()).first()
                if dup:
                    logger.info("[딥바이v3.6] 중복 거래 기록 스킵: %s %s %d주", name, tx_type, qty)
                    return
                
                commission = price * qty * 0.00015 if tx_type == "BUY" else 0
                tax = price * qty * 0.0018 if tx_type == "SELL" else 0
                memo = f"주문번호: {order_no}" if order_no else None
                
                tx = Transaction(
                    portfolio_id=portfolio.id,
                    stock_code=code,
                    stock_name=name,
                    transaction_type=tx_type,
                    quantity=qty,
                    price=price,
                    total_amount=price * qty,
                    fee=commission,
                    transaction_date=now,
                    tax=tax,
                    memo=memo,
                )
                db.add(tx)

                # Holding 업데이트 (avg_price 컬럼 사용)
                holding = db.query(Holding).filter(
                    Holding.portfolio_id == portfolio.id,
                    Holding.stock_code == code
                ).first()
                
                if tx_type == "BUY":
                    if holding:
                        total_cost = holding.avg_price * holding.quantity + price * qty
                        total_qty = holding.quantity + qty
                        holding.avg_price = total_cost / total_qty
                        holding.quantity = total_qty
                    else:
                        holding = Holding(
                            portfolio_id=portfolio.id,
                            stock_code=code,
                            stock_name=name,
                            quantity=qty,
                            avg_price=price,
                        )
                        db.add(holding)
                elif tx_type == "SELL" and holding:
                    holding.quantity = holding.quantity - qty
                    if holding.quantity <= 0:
                        db.delete(holding)

                db.commit()
            except Exception as e:
                db.rollback()
                logger.error("[딥바이v3.6] DB 오류: %s", e)
            finally:
                db.close()
        except Exception as e:
            logger.error("[딥바이v3.6] DB 저장 실패: %s", e)

    def _is_market_hours(self, now: datetime) -> bool:
        if now.weekday() >= 5:
            return False
        if now.hour < 9:
            return False
        if now.hour > 15 or (now.hour == 15 and now.minute > 20):
            return False
        return True
    
    def get_trailing_status(self) -> Dict:
        result = {}
        for code, state in self.trailing_state.items():
            holding = self.holdings_cache.get(code, {})
            result[code] = {
                **state,
                "name": holding.get("name", code),
                "qty": holding.get("qty", 0),
                "avg_price": holding.get("avg_price", 0)
            }

        return result


    def _sell_one_share_on_peak(self, code: str, name: str, current_price: float, avg_price: float, qty: int):
        """삼성 신고점 갱신 시 1주 매도 (최소 1주 보유 유지, 최소 수익률 3%)"""
        try:
            # 최소 수익률 체크 (+3% 미만이면 스킵)
            if avg_price > 0:
                profit_pct = (current_price - avg_price) / avg_price
                if profit_pct < self.PEAK_SELL_MIN_PCT:
                    logger.info("[삼성신고점] %s 매도 스킵: 수익률 %.2f%% < %.1f%%", name, profit_pct * 100, self.PEAK_SELL_MIN_PCT * 100)
                    return

            # 최소 1주 보유 체크
            if code in self.SAMSUNG_CODES and qty <= self.SAMSUNG_MIN_HOLD_QTY:
                logger.info("[삼성신고점] %s 매도 스킵: 최소 %d주 보유 유지 (현재 %d주)", name, self.SAMSUNG_MIN_HOLD_QTY, qty)
                return

            # [FIX 2026-02-25] 직전매도가 이하에서는 신고가매도 금지 (고정매도 블록 우회 방지)
            last_sell_price = self.last_sell_prices.get(code, 0)
            if last_sell_price > 0 and current_price <= last_sell_price:
                logger.info(
                    "[삼성신고점] %s 매도 스킵: 현재가(%s) ≤ 직전매도가(%s)",
                    name,
                    format(int(current_price), ","),
                    format(int(last_sell_price), ","),
                )
                return
            
            with self._sell_lock:
                if code in self._selling_codes:
                    return
                self._selling_codes.add(code)
            
            if not self.kis:
                from backend.services.kis_api_service import kis_api_service
                self.kis = kis_api_service
            
            # virtual 모드: 실제 매도 없이 매도가만 갱신
            if self.get_mode(code) == "virtual":
                self.last_sell_prices[code] = current_price
                logger.info("[삼성신고점] 👻 %s 가상매도 (신고가) @ %s원 → 매도가 갱신", name, format(int(current_price), ","))
                import time as _time
                self._last_sell_time[code] = _time.time()
            else:
                result = self.kis.send_order(code, 1, 0, "1", "01")
                
                if result and result.get("order_no"):
                    profit_pct = (current_price - avg_price) / avg_price
                    logger.info("[삼성신고점] ✅ %s 1주 매도 완료 (수익 +%.2f%%)", name, profit_pct * 100)
                    
                    self._send_notification_sync(
                        "🎯 삼성 신고점 매도: %s 1주 @ %s원 (수익 +%.1f%%)" % 
                        (name, format(int(current_price), ","), profit_pct * 100)
                    )
                    self._save_transaction(code, name, "SELL", 1, current_price, order_no=result.get("order_no"))
                    self.last_sell_prices[code] = current_price

                if code in self.trailing_state:
                    prev_peak_sell = self.trailing_state[code].get("last_peak_sell_price", 0)
                    self.trailing_state[code]["last_peak_sell_price"] = max(prev_peak_sell, current_price)
                
                # [FIX 2026-02-23] 매도 쿨다운 타임스탬프 기록
                import time as _time
                self._last_sell_time[code] = _time.time()
                
                if code in self.holdings_cache:
                    self.holdings_cache[code]["qty"] -= 1
        except Exception as e:
            logger.error("[삼성신고점] 매도 오류 (%s): %s", name, e)
        finally:
            with self._sell_lock:
                self._selling_codes.discard(code)


# 싱글톤
simple_deep_buy = SimpleDeepBuyStrategy()

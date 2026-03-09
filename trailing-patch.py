#!/usr/bin/env python3
"""트레일링 스탑 개선: 고점 대비 하락폭 비례 분할매도"""
import re

FILE = "/Users/ppak/개발/stock/backend/services/simple_deep_buy.py"

with open(FILE, 'r') as f:
    content = f.read()

original = content

# === 1. 상수 변경 ===
# TRAILING_TRIGGER 0.035 → 0.01
content = content.replace(
    "TRAILING_TRIGGER = 0.035      # +3.5% 수익 시 트레일링 시작",
    "TRAILING_TRIGGER = 0.01       # +1.0% 수익 시 트레일링 시작"
)

# TRAILING_STOP_PCT 아래에 새 상수 추가
content = content.replace(
    "TRAILING_STOP_PCT = 0.015     # 고점 대비 -1.5% 하락 시 매도",
    "TRAILING_STOP_PCT = 0.015     # (레거시) 고점 대비 -1.5% 하락 시 매도\n"
    "    TRAILING_SELL_START = 0.005    # 고점 대비 -0.5%부터 매도 시작\n"
    "    TRAILING_SELL_STEP = 0.005     # -0.5% 간격으로 매도 체크"
)

# === 2. _create_default_state 에 last_sold_drop_level 추가 ===
content = content.replace(
    '''    def _create_default_state(self) -> Dict:
        return {
            "active": False,
            "peak_price": 0,
            "stop_price": 0,
            "stop_hit_time": None,
            "waiting_for_recovery": False,
            "last_peak_sell_price": 0  # 마지막 신고가 매도 가격
        }''',
    '''    def _create_default_state(self) -> Dict:
        return {
            "active": False,
            "peak_price": 0,
            "stop_price": 0,
            "stop_hit_time": None,
            "waiting_for_recovery": False,
            "last_peak_sell_price": 0,  # 마지막 신고가 매도 가격
            "last_sold_drop_level": 0,  # 마지막 매도 발생 하락 레벨
        }'''
)

# === 3. on_price_update 전체 교체 ===
# 기존 on_price_update 찾기
old_on_price = '''    """실시간 가격 콜백 - 트레일링 모드에서만 동작"""
        
        # fixed 모드면 무시
        if self.get_mode() == "fixed":
            return
        
        try:
            holding = self.holdings_cache.get(code)
            if not holding:
                return
            
            avg_price = holding["avg_price"]
            qty = holding["qty"]
            name = holding.get("name", code)
            
            state = self.trailing_state.get(code, self._create_default_state())
            
            # 회복 대기 중
            if state.get("waiting_for_recovery"):
                self._check_recovery(code, name, current_price, avg_price, qty, state)
                return
            
            # 트레일링 상태 업데이트
            state = self._update_trailing_state(code, current_price, avg_price, name, state, qty)
            
            # 스톱 도달 체크
            if state["active"] and current_price <= state["stop_price"]:
                self._handle_stop_hit(code, name, current_price, avg_price, qty, state)
                
        except Exception as e:
            logger.error("[딥바이v3.6] 실시간 가격 처리 오류 (%s): %s", code, e)'''

new_on_price = '''    """실시간 가격 콜백 - 트레일링 모드에서만 동작 (v4: 고점 대비 분할매도)"""
        
        # fixed 모드면 무시
        if self.get_mode() == "fixed":
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
            logger.error("[트레일링v4] 실시간 가격 처리 오류 (%s): %s", code, e)'''

content = content.replace(old_on_price, new_on_price)

# === 4. _update_trailing_state 교체 (간소화) ===
# 기존 _update_trailing_state 전체를 찾아서 교체
# 시작: def _update_trailing_state
# 끝: self.trailing_state[code] = state / return state

old_update = '''    def _update_trailing_state(self, code: str, current_price: float, 
                               avg_price: float, name: str, state: dict, qty: int = 0) -> dict:
        """트레일링 상태 업데이트 + 누적 개미떨구기 측정"""
        profit_pct = (current_price - avg_price) / avg_price
        
        if profit_pct >= self.TRAILING_TRIGGER:
            if not state["active"]:
                state["active"] = True
                state["peak_price"] = current_price
                state["stop_price"] = current_price * (1 - self.TRAILING_STOP_PCT)
                state["name"] = name
                state["shakeout_checks"] = []  # 초기화
                state["last_check_drop"] = 0
                logger.info("[트레일링] 🎯 %s 활성화! 고점=%s, 스톱=%s", 
                           name, format(int(current_price), ","), format(int(state["stop_price"]), ","))
            
            elif current_price > state["peak_price"]:
                state["peak_price"] = current_price
                state["stop_price"] = current_price * (1 - self.TRAILING_STOP_PCT)
                state["shakeout_checks"] = []  # 고점 갱신 시 초기화

                # 삼성 종목 신고가 매도는 20분 단위 체크에서 처리 (_run_cycle)
                # (실시간 매도 비활성화)
                state["last_check_drop"] = 0
                logger.info("[트레일링] 📈 %s 고점 갱신! %s, 스톱=%s", 
                           name, format(int(current_price), ","), format(int(state["stop_price"]), ","))
            
            else:
                # 고점 대비 하락률 계산
                drop_from_peak = (state["peak_price"] - current_price) / state["peak_price"]
                
                # -0.5%부터 0.2% 간격으로 누적 측정
                if drop_from_peak >= self.SHAKEOUT_CHECK_START:
                    last_drop = state.get("last_check_drop", 0)
                    
                    # 새로운 측정 구간 진입 시
                    if drop_from_peak >= last_drop + self.SHAKEOUT_CHECK_INTERVAL:
                        score = self._get_shakeout_score(code, name)
                        state["shakeout_checks"].append({
                            "drop_pct": round(drop_from_peak * 100, 1),
                            "score": score,
                            "time": time.time()
                        })
                        state["last_check_drop"] = drop_from_peak
                        
                        checks = state["shakeout_checks"]
                        avg_score = sum(c["score"] for c in checks) / len(checks) if checks else 0
                        logger.info("[개미떨구기] 📊 %s 측정 #%d: 하락 -%.1f%%, 점수 %d (평균 %.1f)", 
                                   name, len(checks), drop_from_peak * 100, score, avg_score)
        
        self.trailing_state[code] = state
        return state'''

new_update = '''    def _check_trailing_sell(self, code: str, name: str, current_price: float,
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
                self._save_transaction(code, name, "SELL", sell_qty, current_price)
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
        return state'''

content = content.replace(old_update, new_update)

# === 5. _run_cycle에서 trailing 모드일 때 신고가매도 스킵 ===
# 삼성 종목 신고가 체크 부분을 trailing 모드에서 스킵
content = content.replace(
    '''                # 삼성 종목 신고가 체크 (20분 단위) — 고정매도 후 남은 수량 반영
                adjusted_qty = qty - sold_in_cycle
                if code in self.SAMSUNG_CODES and adjusted_qty > 0:''',
    '''                # 삼성 종목 신고가 체크 (20분 단위, fixed 모드만) — 고정매도 후 남은 수량 반영
                adjusted_qty = qty - sold_in_cycle
                if code in self.SAMSUNG_CODES and adjusted_qty > 0 and self.get_mode(code) == "fixed":'''
)

# === 6. trailing 모드 20분 주기 백업 체크 추가 ===
# _run_cycle 매수 실행 직전에 trailing 백업 체크 삽입
content = content.replace(
    '''            # 매수 실행
            if should_buy:''',
    '''            # trailing 모드 20분 주기 백업 체크 (WebSocket 미연결 시 대비)
            if not should_buy and self.get_mode(code) == "trailing":
                state = self.trailing_state.get(code, {})
                if state.get("active") and state.get("peak_price", 0) > 0:
                    self._check_trailing_sell(code, name, current_price, avg_price, qty, state)

            # 매수 실행
            if should_buy:'''
)

# === 7. docstring 업데이트 ===
content = content.replace(
    '"""단순 딥바이 전략 v3.6',
    '"""단순 딥바이 전략 v4.0'
)
content = content.replace(
    '  - trailing: 실시간 트레일링 스톱 (웹소켓)',
    '  - trailing: 고점 대비 분할매도 트레일링 (웹소켓)'
)
content = content.replace(
    '[v3.6] 전략 모드 스위칭 (API 런타임 변경)',
    '[v3.6] 전략 모드 스위칭 (API 런타임 변경)\n[v4.0] 트레일링 개선: 고점 대비 하락폭 비례 분할매도'
)

# === 검증 ===
changes = []
if "TRAILING_TRIGGER = 0.01" in content:
    changes.append("✅ TRAILING_TRIGGER 0.035 → 0.01")
if "TRAILING_SELL_START = 0.005" in content:
    changes.append("✅ TRAILING_SELL_START 추가")
if "TRAILING_SELL_STEP = 0.005" in content:
    changes.append("✅ TRAILING_SELL_STEP 추가")
if "last_sold_drop_level" in content:
    changes.append("✅ last_sold_drop_level 상태 추가")
if "_check_trailing_sell" in content:
    changes.append("✅ _check_trailing_sell 메서드 추가")
if "_execute_trailing_sell" in content:
    changes.append("✅ _execute_trailing_sell 메서드 추가")
if '트레일링v4' in content:
    changes.append("✅ 로그 태그 [트레일링v4]")
if 'self.get_mode(code) == "fixed":' in content:
    changes.append("✅ 신고가매도 fixed 모드 제한")
if "trailing 모드 20분 주기 백업" in content:
    changes.append("✅ trailing 20분 백업 체크 추가")
if "v4.0" in content:
    changes.append("✅ 버전 v4.0")

print("=== 변경사항 ===")
for c in changes:
    print(c)
print(f"\n총 {len(changes)}/10 항목 적용")

if len(changes) >= 8:
    with open(FILE, 'w') as f:
        f.write(content)
    print("\n✅ 파일 저장 완료!")
else:
    print("\n❌ 변경사항 부족 — 저장 안 함")
    # 매칭 안 된 항목 디버그
    if "TRAILING_TRIGGER = 0.01" not in content:
        print("  MISS: TRAILING_TRIGGER")
    if "_check_trailing_sell" not in content:
        print("  MISS: _check_trailing_sell")
    if "트레일링v4" not in content:
        print("  MISS: on_price_update 교체 안 됨")

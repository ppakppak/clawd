#!/usr/bin/env python3
"""Add virtual sell mode to simple_deep_buy.py"""

filepath = '/Users/ppak/개발/stock/backend/services/simple_deep_buy.py'
with open(filepath, 'r') as f:
    content = f.read()

fixes = 0

# 1. SellMode 타입 확장
old = 'SellMode = Literal["trailing", "fixed"]'
new = 'SellMode = Literal["trailing", "fixed", "virtual"]'
if old in content:
    content = content.replace(old, new, 1)
    fixes += 1
    print('Fix 1: SellMode type extended')

# 2. set_mode 유효성 검사
old = """if mode not in ("trailing", "fixed"):
            return {"success": False, "error": f"Invalid mode: {mode}. Use 'trailing' or 'fixed'"}"""
new = """if mode not in ("trailing", "fixed", "virtual"):
            return {"success": False, "error": f"Invalid mode: {mode}. Use 'trailing', 'fixed', or 'virtual'"}"""
if old in content:
    content = content.replace(old, new, 1)
    fixes += 1
    print('Fix 2: set_mode validation updated')

# 3. on_realtime_price: virtual도 fixed처럼 실시간 트레일링 제외
old = """        # [FIX 2026-02-23] 종목별 모드 체크 (글로벌 모드가 trailing이어도 fixed 종목은 제외)
        if self.get_mode(code) == "fixed":
            return"""
new = """        # [FIX 2026-02-23] 종목별 모드 체크 (글로벌 모드가 trailing이어도 fixed/virtual 종목은 제외)
        if self.get_mode(code) in ("fixed", "virtual"):
            return"""
if old in content:
    content = content.replace(old, new, 1)
    fixes += 1
    print('Fix 3: on_realtime_price excludes virtual')

# 4. _run_cycle: virtual 모드에서 가상매도
old = """                # 매도 체크 (fixed 모드만)
                if self.get_mode(code) == "fixed":
                    sold_in_cycle = await self._check_fixed_sell(code, name, current_price, avg_price, qty)"""
new = """                # 매도 체크 (fixed/virtual 모드)
                effective_mode = self.get_mode(code)
                if effective_mode == "fixed":
                    sold_in_cycle = await self._check_fixed_sell(code, name, current_price, avg_price, qty)
                elif effective_mode == "virtual":
                    sold_in_cycle = self._check_virtual_sell(code, name, current_price, avg_price, qty)"""
if old in content:
    content = content.replace(old, new, 1)
    fixes += 1
    print('Fix 4: _run_cycle virtual sell check')

# 5. 신고가매도 부분도 virtual 처리
old = 'if code in self.SAMSUNG_CODES and adjusted_qty > 0 and sold_in_cycle == 0 and self.get_mode(code) == "fixed":'
new = 'if code in self.SAMSUNG_CODES and adjusted_qty > 0 and sold_in_cycle == 0 and self.get_mode(code) in ("fixed", "virtual"):'
if old in content:
    content = content.replace(old, new, 1)
    fixes += 1
    print('Fix 5: peak sell includes virtual mode')

# 6. _sell_one_share_on_peak에 virtual 분기 추가
old = """            result = self.kis.send_order(code, 1, 0, "1", "01")
            
            if result and result.get("order_no"):
                profit_pct = (current_price - avg_price) / avg_price
                logger.info("[삼성신고점] ✅ %s 1주 매도 완료 (수익 +%.2f%%)", name, profit_pct * 100)
                
                self._send_notification_sync(
                    "🎯 삼성 신고점 매도: %s 1주 @ %s원 (수익 +%.1f%%)" % 
                    (name, format(int(current_price), ","), profit_pct * 100)
                )
                self._save_transaction(code, name, "SELL", 1, current_price, order_no=result.get("order_no"))
                self.last_sell_prices[code] = current_price"""
new = """            # virtual 모드: 실제 매도 없이 매도가만 갱신
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
                    self.last_sell_prices[code] = current_price"""
if old in content:
    content = content.replace(old, new, 1)
    fixes += 1
    print('Fix 6: _sell_one_share_on_peak virtual branch')

# 7. _check_virtual_sell 메서드 추가 (_check_fixed_sell 바로 뒤, "=== 매도 실행 ===" 마커 앞)
marker = '    # === 매도 실행 ==='
virtual_method = """    def _check_virtual_sell(self, code: str, name: str, current_price: float,
                              avg_price: float, qty: int) -> int:
        \"\"\"가상매도: 실제 매도 없이 매도가만 갱신 (virtual 모드)\"\"\"
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

    """ + marker

if marker in content:
    content = content.replace(marker, virtual_method, 1)
    fixes += 1
    print('Fix 7: _check_virtual_sell method added')

if fixes > 0:
    with open(filepath, 'w') as f:
        f.write(content)
    print(f'\nDone: {fixes} fixes applied')
else:
    print('ERROR: No fixes applied')

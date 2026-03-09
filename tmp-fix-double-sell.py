#!/usr/bin/env python3
"""Fix double-sell bug: _check_fixed_sell returns sold qty, _run_cycle adjusts qty before peak sell"""

import re

FILE = "/Users/ppak/개발/stock/backend/services/simple_deep_buy.py"

with open(FILE, "r") as f:
    content = f.read()

# 1. _check_fixed_sell: return sold qty (0 if nothing sold)
# Change the function to return the number of shares actually sold

old_fixed_sell = '''    async def _check_fixed_sell(self, code: str, name: str, current_price: float,
                                 avg_price: float, qty: int):
        """고정 간격 매도 체크 (+1.5%, 기준가 = 평단가)"""
        profit_pct = (current_price - avg_price) / avg_price
        
        if profit_pct >= self.SELL_RISE_PCT:
            sell_qty = self._calc_quantity(qty, profit_pct)
            if sell_qty <= 0:
                            sell_qty = 1  # 최소 1주 매도
            
            logger.info("[고정매도] %s: 평단가(%s) 기준 +%.2f%% ≥ +%.1f%% → 매도 %d주", 
                        name, format(int(avg_price), ","),
                        profit_pct * 100, self.SELL_RISE_PCT * 100, sell_qty)
            
            await self._execute_sell_async(code, name, current_price, avg_price, sell_qty, "fixed")'''

new_fixed_sell = '''    async def _check_fixed_sell(self, code: str, name: str, current_price: float,
                                 avg_price: float, qty: int) -> int:
        """고정 간격 매도 체크 (+1.5%, 기준가 = 평단가). Returns: 실제 매도된 수량"""
        profit_pct = (current_price - avg_price) / avg_price
        
        if profit_pct >= self.SELL_RISE_PCT:
            sell_qty = self._calc_quantity(qty, profit_pct)
            if sell_qty <= 0:
                            sell_qty = 1  # 최소 1주 매도
            
            logger.info("[고정매도] %s: 평단가(%s) 기준 +%.2f%% ≥ +%.1f%% → 매도 %d주", 
                        name, format(int(avg_price), ","),
                        profit_pct * 100, self.SELL_RISE_PCT * 100, sell_qty)
            
            sold = await self._execute_sell_async(code, name, current_price, avg_price, sell_qty, "fixed")
            return sold if sold else 0
        return 0'''

assert old_fixed_sell in content, "_check_fixed_sell not found!"
content = content.replace(old_fixed_sell, new_fixed_sell)

# 2. _execute_sell_async: return sold qty instead of None
old_exec_sell_return = '''            result = self.kis.send_order(code, sell_qty, 0, "1", "01")
            
            if result and result.get("order_no"):
                logger.info("[딥바이v3.6] ✅ %s 고정매도 완료: %d주", name, sell_qty)
                await self._send_notification(
                    "💰 고정 익절: %s %d주 @ %s원 (수익 +%.1f%%)" % 
                    (name, sell_qty, format(int(current_price), ","), profit_pct * 100)
                )
                self._save_transaction(code, name, "SELL", sell_qty, current_price)
                self.last_sell_prices[code] = current_price  # 매도가 저장
                logger.info("[딥바이v3.6] 📝 %s 매도가 저장: %s원", name, format(int(current_price), ","))
                self.update_holdings_cache()
                await self._broadcast_holdings_update()
                
        except Exception as e:
            logger.error("[딥바이v3.6] 매도 오류: %s", e)
        finally:
            with self._sell_lock:
                self._selling_codes.discard(code)'''

new_exec_sell_return = '''            result = self.kis.send_order(code, sell_qty, 0, "1", "01")
            
            if result and result.get("order_no"):
                logger.info("[딥바이v3.6] ✅ %s 고정매도 완료: %d주", name, sell_qty)
                await self._send_notification(
                    "💰 고정 익절: %s %d주 @ %s원 (수익 +%.1f%%)" % 
                    (name, sell_qty, format(int(current_price), ","), profit_pct * 100)
                )
                self._save_transaction(code, name, "SELL", sell_qty, current_price)
                self.last_sell_prices[code] = current_price  # 매도가 저장
                logger.info("[딥바이v3.6] 📝 %s 매도가 저장: %s원", name, format(int(current_price), ","))
                self.update_holdings_cache()
                await self._broadcast_holdings_update()
                return sell_qty
            return 0
                
        except Exception as e:
            logger.error("[딥바이v3.6] 매도 오류: %s", e)
            return 0
        finally:
            with self._sell_lock:
                self._selling_codes.discard(code)'''

assert old_exec_sell_return in content, "_execute_sell_async return not found!"
content = content.replace(old_exec_sell_return, new_exec_sell_return)

# 3. _run_cycle: capture sold qty from fixed sell, adjust qty before peak sell
old_run_cycle_sell = '''            if should_buy:
                logger.info("[딥바이v3.6] %s 매수 조건 충족 → 매도 스킵 (매수 우선)", name)
            else:
                # 매도 체크 (fixed 모드만)
                if self.get_mode(code) == "fixed":
                    await self._check_fixed_sell(code, name, current_price, avg_price, qty)
                
                # 삼성 종목 신고가 체크 (20분 단위)
                if code in self.SAMSUNG_CODES:
                    state = self.trailing_state.get(code, {})
                    last_peak_sell = state.get("last_peak_sell_price", 0)
                    if current_price > last_peak_sell:
                        logger.info("[신고가매도] %s 신고가 갱신! 현재가=%s > 이전고점=%s",
                                   name, format(int(current_price), ","), format(int(last_peak_sell), ","))
                        self._sell_one_share_on_peak(code, name, current_price, avg_price, qty)
                        if code in self.trailing_state:
                            self.trailing_state[code]["last_peak_sell_price"] = current_price'''

new_run_cycle_sell = '''            if should_buy:
                logger.info("[딥바이v3.6] %s 매수 조건 충족 → 매도 스킵 (매수 우선)", name)
            else:
                sold_in_cycle = 0
                
                # 매도 체크 (fixed 모드만)
                if self.get_mode(code) == "fixed":
                    sold_in_cycle = await self._check_fixed_sell(code, name, current_price, avg_price, qty)
                
                # 삼성 종목 신고가 체크 (20분 단위) — 고정매도 후 남은 수량 반영
                adjusted_qty = qty - sold_in_cycle
                if code in self.SAMSUNG_CODES and adjusted_qty > 0:
                    state = self.trailing_state.get(code, {})
                    last_peak_sell = state.get("last_peak_sell_price", 0)
                    if current_price > last_peak_sell:
                        logger.info("[신고가매도] %s 신고가 갱신! 현재가=%s > 이전고점=%s (잔여 %d주)",
                                   name, format(int(current_price), ","), format(int(last_peak_sell), ","), adjusted_qty)
                        self._sell_one_share_on_peak(code, name, current_price, avg_price, adjusted_qty)
                        if code in self.trailing_state:
                            self.trailing_state[code]["last_peak_sell_price"] = current_price'''

assert old_run_cycle_sell in content, "_run_cycle sell block not found!"
content = content.replace(old_run_cycle_sell, new_run_cycle_sell)

with open(FILE, "w") as f:
    f.write(content)

print("✅ Double-sell bug fixed!")
print("Changes:")
print("  1. _check_fixed_sell now returns sold qty (int)")
print("  2. _execute_sell_async now returns sold qty (int)")  
print("  3. _run_cycle: adjusts qty after fixed sell before peak sell")

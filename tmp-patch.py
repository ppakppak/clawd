# -*- coding: utf-8 -*-
import sys

filepath = sys.argv[1]
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_block = [
    "            # 블랙리스트 체크\n",
    "            if is_blacklisted(code):\n",
    "                logger.debug('[딥바이] %s 블랙리스트 → 매수 스킵', name)\n",
    "                continue\n",
    "\n",
    "            # 매수 조건 먼저 판단 (매수 우선 정책)\n",
    "            last_sell = self.last_sell_prices.get(code, 0)\n",
    "            buy_ref_price = max(avg_price, last_sell) if last_sell > 0 else avg_price\n",
    '            buy_ref_label = "매도가" if last_sell > avg_price else "평단가"\n',
    "            drop_from_ref = (buy_ref_price - current_price) / buy_ref_price\n",
    "            should_buy = drop_from_ref >= self.BUY_DROP_PCT\n",
    "\n",
    "            if should_buy:\n",
    '                logger.info("[딥바이v3.6] %s 매수 조건 충족 → 매도 스킵 (매수 우선)", name)\n',
    "            else:\n",
    "                # 매도 체크 (fixed 모드만)\n",
    '                if self.get_mode(code) == "fixed":\n',
    "                    await self._check_fixed_sell(code, name, current_price, avg_price, qty)\n",
    "                \n",
    "                # 삼성 종목 신고가 체크 (20분 단위)\n",
    "                if code in self.SAMSUNG_CODES:\n",
    "                    state = self.trailing_state.get(code, {})\n",
    '                    last_peak_sell = state.get("last_peak_sell_price", 0)\n',
    "                    if current_price > last_peak_sell:\n",
    '                        logger.info("[신고가매도] %s 신고가 갱신! 현재가=%s > 이전고점=%s",\n',
    '                                   name, format(int(current_price), ","), format(int(last_peak_sell), ","))\n',
    "                        self._sell_one_share_on_peak(code, name, current_price, avg_price, qty)\n",
    "                        if code in self.trailing_state:\n",
    '                            self.trailing_state[code]["last_peak_sell_price"] = current_price\n',
    "\n",
    "            # 매수 실행\n",
]

# Replace lines 1011-1037 (index 1010-1036)
lines[1010:1037] = new_block

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("OK - patched")

# Verify
with open(filepath, "r", encoding="utf-8") as f:
    vlines = f.readlines()
for i in range(1008, 1052):
    print(f"{i+1}: {vlines[i]}", end="")

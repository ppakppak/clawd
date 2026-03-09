# -*- coding: utf-8 -*-
import sys

filepath = sys.argv[1]
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Fix lines 1041-1048 (index 1040-1047)
# Change "# 매수 실행" block to be under "if should_buy:"
new_block = [
    "\n",
    "            # 매수 실행\n",
    "            if should_buy:\n",
    "                buy_qty = self._calc_quantity(qty, drop_from_ref)\n",
    "                if buy_qty > 0:\n",
    "                    required_cash = current_price * buy_qty * 1.001\n",
    "                    if cash >= required_cash:\n",
    "                        await self._execute_buy(code, name, current_price, buy_qty,\n",
    '                            "%s(%s) 대비 -%.1f%%" % (buy_ref_label, format(int(buy_ref_price), ","), drop_from_ref * 100))\n',
    "                        cash -= required_cash\n",
]

# Replace lines 1040-1048 (the broken "# 매수 실행" section)
lines[1040:1049] = new_block

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("OK - fixed indentation")

with open(filepath, "r", encoding="utf-8") as f:
    vlines = f.readlines()
for i in range(1015, 1055):
    print(f"{i+1}: {vlines[i]}", end="")

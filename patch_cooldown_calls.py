#!/usr/bin/env python3
"""
Patch script to update check_sell_signal to pass db and portfolio_id to cooldown methods
"""

service_file = 'backend/services/samsung_deep_buy_service.py'
with open(service_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update check_tier_cooldown call
old_check_call = '''        # [v2.4] 티어 쿨다운 체크 - 수익률 상승 시에만 다음 티어 실행
        tier_cooldown_ok = cls.check_tier_cooldown(stock_code, profit_rate)
        if not tier_cooldown_ok:
            last_profit = cls.get_last_sell_profit(stock_code)
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (상승 대기 - 마지막 {last_profit:.1f}%)"
            logger.debug(f"[딥바이] {stock_name}: 수익률 미상승 - 현재 {profit_rate:.1f}% <= 마지막 {last_profit:.1f}%")
            return result'''

new_check_call = '''        # [v2.4] 티어 쿨다운 체크 - 수익률 상승 시에만 다음 티어 실행 (DB 기반)
        tier_cooldown_ok = cls.check_tier_cooldown(db, stock_code, profit_rate, holding.portfolio_id)
        if not tier_cooldown_ok:
            last_profit = cls.get_last_sell_profit(db, stock_code, holding.portfolio_id)
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (상승 대기 - 마지막 {last_profit:.1f}%)"
            logger.debug(f"[딥바이] {stock_name}: 수익률 미상승 - 현재 {profit_rate:.1f}% <= 마지막 {last_profit:.1f}%")
            return result'''

if old_check_call in content:
    content = content.replace(old_check_call, new_check_call)
    print('Step 1 완료: check_tier_cooldown/get_last_sell_profit 호출 업데이트')
else:
    print('Step 1 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# 2. Update set_last_sell_profit call
old_set_call = '''            # [v2.4] 마지막 매도 수익률 기록 - 이보다 상승해야 다음 티어 실행
            cls.set_last_sell_profit(stock_code, profit_rate)'''

new_set_call = '''            # [v2.4] 마지막 매도 수익률 기록 - 이보다 상승해야 다음 티어 실행 (DB 저장)
            cls.set_last_sell_profit(db, stock_code, profit_rate, holding.portfolio_id)'''

if old_set_call in content:
    content = content.replace(old_set_call, new_set_call)
    print('Step 2 완료: set_last_sell_profit 호출 업데이트')
else:
    print('Step 2 스킵: 이미 변경되었거나 위치를 찾을 수 없음')

# Write the modified file
with open(service_file, 'w', encoding='utf-8') as f:
    f.write(content)

print('\n호출부 패치 완료!')

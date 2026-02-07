#!/usr/bin/env python3
"""
Patch script for check_sell_signal function in samsung_deep_buy_service.py
Adds tier cooldown check to prevent cascading sells
"""
import re

# Read the file
filepath = 'backend/services/samsung_deep_buy_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add tier cooldown check after the sell lock check
old_lock_check = '''        # [v2.3] 매도 락 체크 - 동시 매도 방지
        logger.info(f"[딥바이-신호] {stock_code}: 매도 락 체크 시작")
        if cls.is_sell_locked(stock_code):
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (매도 락 활성화 - 대기)"
            logger.info(f"[딥바이] {stock_name}: 매도 락 활성화 상태 - 매도 스킵")
            return result
        logger.info(f"[딥바이-신호] {stock_code}: 매도 락 체크 완료")

        # 오늘 매도 횟수 확인'''

new_lock_check = '''        # [v2.3] 매도 락 체크 - 동시 매도 방지
        logger.info(f"[딥바이-신호] {stock_code}: 매도 락 체크 시작")
        if cls.is_sell_locked(stock_code):
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (매도 락 활성화 - 대기)"
            logger.info(f"[딥바이] {stock_name}: 매도 락 활성화 상태 - 매도 스킵")
            return result
        logger.info(f"[딥바이-신호] {stock_code}: 매도 락 체크 완료")

        # [v2.4] 티어 쿨다운 체크 - 연속 티어 매도 방지
        # 수익률이 이전 티어 아래로 떨어져야 다음 티어 실행 가능
        tier_cooldown_ok = cls.check_tier_cooldown(stock_code, profit_rate)
        if not tier_cooldown_ok:
            result["recommendation_text"] = f"수익 {profit_rate:.1f}% (티어 쿨다운 - 하락 대기)"
            logger.info(f"[딥바이] {stock_name}: 티어 쿨다운 중 - 수익률이 이전 티어 아래로 떨어져야 다음 매도 가능")
            return result

        # 오늘 매도 횟수 확인'''

if old_lock_check in content:
    content = content.replace(old_lock_check, new_lock_check)
    print('Step 1 완료: 티어 쿨다운 체크 추가')
else:
    print('Step 1 실패: 매도 락 체크 위치를 찾을 수 없음')

# 2. Add tier threshold setting after successful sell signal
old_sell_signal = '''            result["recommendation"] = "PARTIAL_SELL"
            result["recommendation_text"] = f"딥바이 {tier_pct}% 익절 → {int(sell_ratio*100)}% 매도"
            result["quantity"] = sell_qty
            result["sell_score"] = 70 + target_tier_idx * 5  # 티어가 높을수록 점수 증가
            result["is_locked"] = True
            result["signals"].append({
                "type": "TIERED_PROFIT",
                "level": "HIGH",
                "message": f"수익률 {profit_rate:.1f}% ≥ {tier_pct}% (티어 {target_tier_idx+1}/{len(cls.SELL_TIERS)}) → {sell_qty}주 매도",
                "score": result["sell_score"],
                "tier_pct": tier_pct,
                "sell_ratio": sell_ratio
            })
            logger.info(f"[딥바이] {stock_name}: {tier_pct}% 티어 익절! 수익 {profit_rate:.1f}%, {quantity}주 → {sell_qty}주 매도")'''

new_sell_signal = '''            result["recommendation"] = "PARTIAL_SELL"
            result["recommendation_text"] = f"딥바이 {tier_pct}% 익절 → {int(sell_ratio*100)}% 매도"
            result["quantity"] = sell_qty
            result["sell_score"] = 70 + target_tier_idx * 5  # 티어가 높을수록 점수 증가
            result["is_locked"] = True
            result["signals"].append({
                "type": "TIERED_PROFIT",
                "level": "HIGH",
                "message": f"수익률 {profit_rate:.1f}% ≥ {tier_pct}% (티어 {target_tier_idx+1}/{len(cls.SELL_TIERS)}) → {sell_qty}주 매도",
                "score": result["sell_score"],
                "tier_pct": tier_pct,
                "sell_ratio": sell_ratio
            })
            logger.info(f"[딥바이] {stock_name}: {tier_pct}% 티어 익절! 수익 {profit_rate:.1f}%, {quantity}주 → {sell_qty}주 매도")

            # [v2.4] 티어 쿨다운 설정 - 다음 티어 실행을 위해 수익률이 현재 티어 아래로 떨어져야 함
            cls.set_tier_threshold(stock_code, tier_pct)'''

if old_sell_signal in content:
    content = content.replace(old_sell_signal, new_sell_signal)
    print('Step 2 완료: 티어 쿨다운 설정 추가')
else:
    print('Step 2 실패: 매도 신호 위치를 찾을 수 없음')

# Write the modified content
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('check_sell_signal 패치 완료')

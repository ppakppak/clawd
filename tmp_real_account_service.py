"""
실전투자 계좌 서비스 (API <-> DB 동기화)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.portfolio import Portfolio
from backend.models.holding import Holding
from backend.models.transaction import Transaction
from backend.services.kis_api_service import kis_api_service
from backend.config.trading_config import TradingConfig
import logging

logger = logging.getLogger(__name__)


class RealAccountService:
    """실전투자 계좌 관리 및 동기화 서비스"""

    REAL_PORTFOLIO_NAME = "실전투자 계좌"

    @staticmethod
    def get_or_create_real_portfolio(db: Session) -> Portfolio:
        """
        실전투자 포트폴리오 조회 또는 생성
        """
        portfolio = db.query(Portfolio).filter(
            Portfolio.name == RealAccountService.REAL_PORTFOLIO_NAME
        ).first()

        if not portfolio:
            portfolio = Portfolio(
                name=RealAccountService.REAL_PORTFOLIO_NAME,
                description="KIS API 연동 실전투자 계좌",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)
            logger.info(f"실전투자 포트폴리오 생성: ID={portfolio.id}")

        return portfolio

    @staticmethod
    def sync_holdings(db: Session, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        API 보유 종목을 DB와 동기화
        - API에 있는 종목: DB에 없으면 추가, 있으면 업데이트 (수량, 평단 등)
        - API에 없는 종목: DB에서 삭제 (전량 매도 처리된 것으로 간주)
        - *중요*: 기존 DB의 highest_price, buy_date 등은 유지
        """
        try:
            # 1. API 보유 종목 조회
            api_holdings = kis_api_service.get_holdings()
            
            if api_holdings is None:
                # [CHANGE] 동기화 실패 시 예외 발생 (기존 데이터 표시 방지)
                raise Exception("KIS API 보유 종목 조회 실패 (Sync Failed)")

            api_map = {h["stock_code"]: h for h in api_holdings}

            # 2. DB 보유 종목 조회
            db_holdings = db.query(Holding).filter(
                Holding.portfolio_id == portfolio_id
            ).all()
            db_map = {h.stock_code: h for h in db_holdings}

            # 3. 동기화 로직
            # 3-1. API에 있는 종목 (Insert or Update)
            for stock_code, api_h in api_map.items():
                db_h = db_map.get(stock_code)
                
                if db_h:
                    # 기존 종목 업데이트
                    # 수량이나 평단가가 변경되었는지 확인
                    db_qty = db_h.quantity or 0
                    db_avg = db_h.avg_price or 0
                    db_total = db_h.total_invested or 0
                    
                    if (db_qty != api_h["quantity"] or 
                        abs(db_avg - api_h["average_price"]) > 1 or
                        abs(db_total - api_h["total_cost"]) > 1):
                        
                        db_h.quantity = api_h["quantity"]
                        db_h.avg_price = api_h["average_price"]
                        db_h.total_invested = api_h["total_cost"] # 매입금액 업데이트
                        db_h.stock_name = api_h["stock_name"]
                        db_h.updated_at = datetime.now()
                        
                        logger.info(f"[Sync] {stock_code} 업데이트: Qty={db_h.quantity}, Avg={db_h.avg_price}, Total={db_h.total_invested}")
                else:
                    # 신규 종목 추가
                    new_h = Holding(
                        portfolio_id=portfolio_id,
                        stock_code=stock_code,
                        stock_name=api_h["stock_name"],
                        quantity=api_h["quantity"],
                        avg_price=api_h["average_price"],
                        total_invested=api_h["total_cost"], # 매입금액 저장
                        highest_price=api_h["current_price"], # 초기 최고가는 현재가
                        buy_date=datetime.now(), 
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(new_h)
                    logger.info(f"[Sync] {stock_code} 신규 추가 (매입액: {new_h.total_invested})")

            # 3-2. API에 없는 종목 (Delete)
            # 수량이 0 이상인데 API에 없다면 매도된 것
            for stock_code, db_h in db_map.items():
                if stock_code not in api_map:
                    if db_h.quantity > 0:
                        # [NEW] 오늘 매수한 종목은 API 미반영 상태일 수 있으므로 삭제 방지 (Safe-guard)
                        is_bought_today = False
                        if db_h.buy_date:
                            today_str = datetime.now().strftime("%Y%m%d")
                            buy_date_str = db_h.buy_date.strftime("%Y%m%d")
                            # [CHANGE] 당일 매수라도 10분이 지났으면 API 신뢰 (매도했을 수 있음)
                            minutes_diff = (datetime.now() - db_h.buy_date).total_seconds() / 60
                            if today_str == buy_date_str and minutes_diff < 10:
                                is_bought_today = True
                        
                        if is_bought_today:
                            logger.info(f"[Sync] {stock_code} API 미발견 + 매수 10분 내 -> 유지")
                        else:
                            logger.info(f"[Sync] {stock_code} 전량 매도 감지(또는 10분 경과) -> 삭제")
                            db.delete(db_h)
                    else:
                        # 수량이 0 이하고 API에도 없으면 삭제 (Clean up)
                        logger.info(f"[Sync] {stock_code} 수량 0 & API 미발견 -> 삭제 (Cleanup)")
                        db.delete(db_h)

            db.commit()
            
            # 4. 최신 DB 데이터 반환 (+현재가 등 API 정보 병합 필요할 수도 있지만, 여기선 Sync만 담당)
            # 데이터 리턴은 별도 조회 로직에서 수행 권장
            return api_holdings

        except Exception as e:
            logger.error(f"보유 종목 동기화 실패: {e}")
            db.rollback()
            return []

    @staticmethod
    def sync_transactions(db: Session, portfolio_id: int):
        """
        API 체결 내역을 DB에 동기화
        - 주문번호(ord_no)를 기준으로 중복 방지 (Memo 필드 활용)
        - 같은 주문번호에 대해 수량/가격이 변경되면 업데이트 (체결 누적)
        """
        try:
            # 1. API 체결 내역 조회 (최근 30일 등)
            api_txns = kis_api_service.get_transactions()
            if not api_txns:
                return

            # 2. DB에 이미 있는 내역 조회 (최근 200건)
            recent_db_txns = db.query(Transaction).filter(
                Transaction.portfolio_id == portfolio_id
            ).order_by(Transaction.transaction_date.desc()).limit(200).all()
            
            # 주문번호 -> 트랜잭션 매핑
            # DB의 Memo에 "주문번호: 12345" 형식이 있다고 가정
            db_order_map = {}
            for t in recent_db_txns:
                if t.memo and "주문번호: " in t.memo:
                    try:
                        # "주문번호: 000123" -> "000123" 추출
                        ord_no = t.memo.split("주문번호: ")[1].strip().split()[0]
                        db_order_map[ord_no] = t
                    except:
                        pass

            count_new = 0
            count_update = 0
            
            for tx in api_txns:
                # API의 ord_no (주문번호)를 Key로 사용
                # API ord_no는 숫자일 수도, 문자열일 수도 있음. 문자열로 통일.
                ord_no = str(tx.get("id")) # get_transactions에서 id에 ord_no를 넣었음
                
                # 없는 경우 Skip (주문번호가 없으면 식별 불가)
                if not ord_no or ord_no == "0":
                    continue

                if ord_no in db_order_map:
                    # 기존 내역 존재: 업데이트 확인
                    existing_txn = db_order_map[ord_no]
                    
                    # 수량이 늘어났거나 (추가 체결), 가격이 변했으면 업데이트
                    if (existing_txn.quantity != tx["quantity"] or 
                        existing_txn.price != tx["price"] or
                        existing_txn.total_amount != tx["total_amount"]):
                        
                        logger.info(f"[Sync] Update Transaction: {tx['stock_name']} ({ord_no}) "
                                    f"Qty {existing_txn.quantity}->{tx['quantity']}, "
                                    f"Price {existing_txn.price}->{tx['price']}")
                        
                        existing_txn.quantity = tx["quantity"]
                        existing_txn.price = tx["price"]
                        existing_txn.total_amount = tx["total_amount"]
                        existing_txn.tax = tx["tax"]
                        existing_txn.fee = tx["commission"]
                        existing_txn.updated_at = datetime.now()
                        count_update += 1
                else:
                    # 신규 내역 추가
                    logger.info(f"[Sync] New Transaction: {tx['stock_name']} ({ord_no}) Qty {tx['quantity']}")

                    # [FIX] Holding에서 strategy 조회 (매도 시점의 strategy 정확히 추적)
                    txn_strategy = "standard"  # 기본값
                    
                    # 1. 현재 Holding에서 strategy 조회
                    holding = db.query(Holding).filter(
                        Holding.portfolio_id == portfolio_id,
                        Holding.stock_code == tx["stock_code"]
                    ).first()
                    
                    if holding and holding.strategy:
                        txn_strategy = holding.strategy
                    else:
                        # 2. Holding이 없거나 strategy가 없으면, 딥바이 종목 목록 확인
                        from backend.services.samsung_deep_buy_service import SamsungDeepBuyService
                        if SamsungDeepBuyService.is_target_stock(tx["stock_code"]):
                            txn_strategy = SamsungDeepBuyService.STRATEGY_NAME
                            logger.info(f"[Sync] 딥바이 종목 감지: {tx['stock_name']} → strategy={txn_strategy}")
                        else:
                            # 3. 최근 매수 기록에서 strategy 조회 (매도 전 매수 기록 확인)
                            recent_buy = db.query(Transaction).filter(
                                Transaction.portfolio_id == portfolio_id,
                                Transaction.stock_code == tx["stock_code"],
                                Transaction.transaction_type == "BUY"
                            ).order_by(Transaction.transaction_date.desc()).first()
                            
                            if recent_buy and recent_buy.strategy:
                                txn_strategy = recent_buy.strategy
                                logger.info(f"[Sync] 최근 매수 기록에서 strategy 조회: {tx['stock_name']} → strategy={txn_strategy}")
                            else:
                                logger.warning(f"[Sync] strategy를 찾을 수 없음: {tx['stock_name']} → 기본값 'standard' 사용")

                    new_txn = Transaction(
                        portfolio_id=portfolio_id,
                        stock_code=tx["stock_code"],
                        stock_name=tx["stock_name"],
                        transaction_type=tx["type"],
                        quantity=tx["quantity"],
                        price=tx["price"],
                        total_amount=tx["total_amount"],
                        fee=tx["commission"],
                        tax=tx["tax"],
                        transaction_date=datetime.strptime(tx["transaction_date"], "%Y%m%d %H%M%S"),
                        memo=f"주문번호: {ord_no}",
                        strategy=txn_strategy,  # [FIX] strategy 추가
                        created_at=datetime.now()
                    )
                    db.add(new_txn)
                    count_new += 1
            
            if count_new > 0 or count_update > 0:
                db.commit()
                logger.info(f"[Sync] 거래 완료: 신규 {count_new}건, 업데이트 {count_update}건")

        except Exception as e:
            logger.error(f"거래 내역 동기화 실패: {e}")
            db.rollback()

    @staticmethod
    def buy_stock(
        db: Session,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int, # 0이면 시장가
        portfolio_id: Optional[int] = None,
        strategy: str = "standard",
        order_type: str = "00"  # IOC/FOK 지원: 11=IOC지정가, 12=FOK지정가, 13=IOC시장가
    ) -> Dict[str, Any]:
        """
        실전 매수 주문

        Args:
            order_type: 주문 유형
                - 00: 지정가 (기본)
                - 01: 시장가
                - 11: IOC지정가 (즉시체결/취소 - 슬리피지 감소)
                - 12: FOK지정가 (전량체결/취소)
                - 13: IOC시장가
                - 14: FOK시장가
        """
        try:
            # 1. KIS API 매수 주문
            # ... (skip)

            # [NEW] Holding 정보에 Strategy 저장 (Sync보다 먼저 DB에 선점 기록)
            # 주문 성공 시점에 DB에 Holding 레코드가 없을 수도 있고 있을 수도 있음.
            # 있으면 strategy 업데이트, 없으면 신규 생성하고 strategy 저장.
            is_newly_created = False
            try:
                portfolio_id = portfolio_id if portfolio_id else 1
                holding = db.query(Holding).filter(
                    Holding.portfolio_id == portfolio_id,
                    Holding.stock_code == stock_code
                ).first()

                if holding:
                    holding.strategy = strategy
                else:
                    # 아직 체결 확인 전이지만 Strategy 저장을 위해 미리 생성 (수량 0)
                    # 추후 Sync 시 수량/평단가 업데이트됨
                    new_h = Holding(
                        portfolio_id=portfolio_id,
                        stock_code=stock_code,
                        stock_name=stock_name,
                        quantity=quantity, # [CHANGE] 0 -> quantity (Optimistic Update)
                        avg_price=price,   # [CHANGE] 0 -> price or estimated
                        strategy=strategy,
                        highest_price=0, 
                        buy_date=datetime.now(),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(new_h)
                    is_newly_created = True
                db.commit()
                logger.info(f"매수 전략({strategy}) DB 저장 완료: {stock_name}")

            except Exception as h_e:
                logger.error(f"Holding 전략 저장 실패: {h_e}")

            # 2. KIS 매수 주문 전송
            try:
                result = kis_api_service.send_order(stock_code, quantity, price, "2", order_type)

                if not result:
                    raise Exception("API 매수 주문 실패 (응답 없음)")

                order_no = result.get("order_no")

                logger.info(f"실전 매수 주문 완료: {stock_name}({stock_code}) {quantity}주, 주문번호 {order_no}")

                return {
                    "success": True,
                    "message": f"매수 주문 전송 완료 (주문번호: {order_no})",
                    "order_no": order_no,
                    "quantity": quantity,
                    "price": price,
                    "total_amount": quantity * price # 예상 금액
                }

            except Exception as e:
                # [NEW] 주문가능금액 부족 시 1주 fallback 재주문 (수동/자동매매 공통)
                err_msg = str(e)
                is_insufficient_cash = ("주문가능금액" in err_msg and "초과" in err_msg)

                if is_insufficient_cash and quantity > 1:
                    logger.warning(
                        f"매수 주문가능금액 부족으로 1주 fallback 시도: {stock_name}({stock_code}) "
                        f"{quantity}주 -> 1주"
                    )
                    try:
                        fallback_qty = 1
                        fallback_result = kis_api_service.send_order(stock_code, fallback_qty, price, "2", order_type)

                        if not fallback_result:
                            raise Exception("API 매수 주문 실패 (1주 fallback 응답 없음)")

                        fallback_order_no = fallback_result.get("order_no")

                        logger.info(
                            f"실전 매수 fallback 주문 완료: {stock_name}({stock_code}) "
                            f"{fallback_qty}주, 주문번호 {fallback_order_no}"
                        )

                        return {
                            "success": True,
                            "message": f"매수 주문 전송 완료 (잔고 부족으로 1주 대체, 주문번호: {fallback_order_no})",
                            "order_no": fallback_order_no,
                            "quantity": fallback_qty,
                            "requested_quantity": quantity,
                            "fallback_applied": True,
                            "price": price,
                            "total_amount": fallback_qty * price
                        }
                    except Exception as fallback_e:
                        logger.error(f"1주 fallback 주문도 실패: {fallback_e}")

                # [FIX] 주문 실패 시 DB에 생성했던 Holding 기록 삭제 (Ghost Stock 방지)
                logger.error(f"주문 전송 실패로 Holding 기록 롤백: {e}")

                if is_newly_created:
                    try:
                        failed_holding = db.query(Holding).filter(
                            Holding.portfolio_id == portfolio_id,
                            Holding.stock_code == stock_code
                        ).first()

                        if failed_holding:
                            db.delete(failed_holding)
                            db.commit()
                            logger.info(f"Ghost Holding 삭제 완료 (Rollback): {stock_name}({stock_code})")
                    except Exception as del_e:
                        logger.error(f"Holding 롤백 실패: {del_e}")

                raise e

        except Exception as e:
            logger.error(f"실전 매수 실패: {e}")
            return {"success": False, "message": str(e)}


    @staticmethod
    def sell_stock(
        db: Session,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        portfolio_id: Optional[int] = None,
        order_type: str = "00"  # IOC/FOK 지원
    ) -> Dict[str, Any]:
        """
        실전 매도 주문

        Args:
            order_type: 주문 유형
                - 00: 지정가 (기본)
                - 01: 시장가
                - 11: IOC지정가 (즉시체결/취소)
                - 12: FOK지정가 (전량체결/취소)
                - 13: IOC시장가
                - 14: FOK시장가
        """
        try:
            # [NEW] 비정상 가격 검증 - Mock Data 방지 (2026-01-09)
            # 시장가(price=0)가 아닌 경우에만 검증
            if price > 0:
                holding = db.query(Holding).filter(
                    Holding.portfolio_id == (portfolio_id if portfolio_id else 1),
                    Holding.stock_code == stock_code
                ).first()
                if holding and holding.avg_price > 0:
                    price_ratio = price / holding.avg_price
                    if price_ratio >= 3.0:
                        logger.warning(
                            f"[실전매도차단] 비정상 가격 감지: {stock_name}({stock_code}) "
                            f"평단가={int(holding.avg_price):,}원, 매도가={price:,}원, "
                            f"비율={price_ratio:.1f}배"
                        )
                        return {
                            "success": False,
                            "message": f"비정상 가격으로 매도 차단 (평단가 대비 {price_ratio:.1f}배)"
                        }

            result = kis_api_service.send_order(stock_code, quantity, price, "1", order_type)

            if not result:
                return {"success": False, "message": "API 매도 주문 실패"}

            order_no = result.get("order_no")
            
            logger.info(f"실전 매도 주문 완료: {stock_name}({stock_code}) {quantity}주, 주문번호 {order_no}")

            # [NOTE] Transaction 기록은 sync_transactions()에서 API 체결 내역 기반으로 처리
            # 여기서 기록하면 sync 시 중복 발생 (동일 주문번호로 2건 기록됨)

            return {
                "success": True,
                "message": f"매도 주문 전송 완료 (주문번호: {order_no})",
                "order_no": order_no,
                "quantity": quantity,
                "price": price,
                "total_amount": quantity * price
            }
            
        except Exception as e:
            logger.error(f"실전 매도 실패: {e}")
            return {"success": False, "message": str(e)}

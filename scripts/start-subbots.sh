#!/bin/bash
# start-subbots.sh - 서브봇 멀티 터미널 실행
# Usage: ./start-subbots.sh [stock|project|dev|all|status]

SESSION_NAME="subbots"
CLAWD_DIR="$HOME/clawd"
GATEWAY_TOKEN="47c8a60e26ccc36e131ee7958227dfa72d0d9a3968fc7f77"
GATEWAY_PORT="18789"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 대화형 에이전트 루프
interactive_agent() {
    local AGENT_ID=$1
    local EMOJI=$2
    local NAME=$3
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${EMOJI} ${CYAN}${NAME}${NC} 시작 (종료: Ctrl+C 또는 'exit')"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    while true; do
        echo -ne "${EMOJI} ${CYAN}You:${NC} "
        read -r input
        
        # 종료 조건
        if [[ "$input" == "exit" || "$input" == "quit" || "$input" == "q" ]]; then
            echo -e "${YELLOW}${NAME} 종료${NC}"
            break
        fi
        
        # 빈 입력 무시
        if [[ -z "$input" ]]; then
            continue
        fi
        
        # 에이전트 호출
        echo -e "${EMOJI} ${GREEN}${NAME}:${NC}"
        openclaw agent --agent "$AGENT_ID" --message "$input" 2>&1
        echo ""
    done
}

start_all_tmux() {
    # 기존 세션 있으면 종료
    tmux kill-session -t $SESSION_NAME 2>/dev/null

    echo -e "${GREEN}🚀 서브봇 tmux 세션 시작...${NC}"
    
    # 새 세션 생성 (주식봇)
    tmux new-session -d -s $SESSION_NAME -n "📈stock"
    tmux send-keys -t $SESSION_NAME:0 "cd $CLAWD_DIR && $CLAWD_DIR/scripts/start-subbots.sh stock" C-m
    
    # 과제봇 윈도우
    tmux new-window -t $SESSION_NAME -n "📋project"
    tmux send-keys -t $SESSION_NAME:1 "cd $CLAWD_DIR && $CLAWD_DIR/scripts/start-subbots.sh project" C-m
    
    # 개발봇 윈도우
    tmux new-window -t $SESSION_NAME -n "💻dev"
    tmux send-keys -t $SESSION_NAME:2 "cd $CLAWD_DIR && $CLAWD_DIR/scripts/start-subbots.sh dev" C-m
    
    # 첫 번째 윈도우로 이동
    tmux select-window -t $SESSION_NAME:0
    
    echo -e "${GREEN}✅ 서브봇 세션 생성 완료!${NC}"
    echo ""
    echo -e "접속: ${YELLOW}tmux attach -t $SESSION_NAME${NC}"
    echo ""
    echo "윈도우 전환 (Ctrl+b 누른 후):"
    echo "  0 → 📈 주식봇"
    echo "  1 → 📋 과제봇"
    echo "  2 → 💻 개발봇"
    echo "  n → 다음 윈도우"
    echo "  p → 이전 윈도우"
    echo ""
    echo -e "세션 종료: ${RED}tmux kill-session -t $SESSION_NAME${NC}"
}

case "$1" in
    stock)
        interactive_agent "stock" "📈" "주식봇"
        ;;
    project)
        interactive_agent "project" "📋" "과제봇"
        ;;
    dev)
        interactive_agent "dev" "💻" "개발봇"
        ;;
    all|"")
        start_all_tmux
        ;;
    attach)
        tmux attach -t $SESSION_NAME
        ;;
    kill)
        tmux kill-session -t $SESSION_NAME 2>/dev/null
        echo -e "${RED}서브봇 세션 종료됨${NC}"
        ;;
    status)
        echo -e "${CYAN}=== OpenClaw 에이전트 현황 ===${NC}"
        openclaw agents list
        echo ""
        if tmux has-session -t $SESSION_NAME 2>/dev/null; then
            echo -e "${GREEN}✅ tmux 세션 실행 중${NC}"
            tmux list-windows -t $SESSION_NAME
        else
            echo -e "${YELLOW}⚠️ tmux 세션 없음${NC}"
        fi
        ;;
    *)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  stock   - 📈 주식봇 대화형 시작"
        echo "  project - 📋 과제봇 대화형 시작"
        echo "  dev     - 💻 개발봇 대화형 시작"
        echo "  all     - 모든 서브봇 tmux로 시작 (기본값)"
        echo "  attach  - 실행 중인 세션에 접속"
        echo "  kill    - 서브봇 세션 종료"
        echo "  status  - 에이전트/세션 상태 확인"
        ;;
esac

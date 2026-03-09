# TOPIC_WINDOWS.md

주제별 **물리 분할 운영 (tmux 4분할)**

## tmux 세션
- 세션명: `claw-split`
- 접속: `tmux attach -t claw-split`
- 종료(유지): `Ctrl-b d` (detach)
- 완전 종료: `tmux kill-session -t claw-split`

## pane 매핑
- pane 0: **주식창** (`session: stock-window`)
- pane 1: **개발창** (`session: dev-window`)
- pane 2: **잡무창** (`session: misc-window`)
- pane 3: **제안서창** (`session: proposal-window`)

## tmux 기본 조작
- pane 이동: `Ctrl-b` 후 방향키
- pane 확대/복귀: `Ctrl-b z`
- 마우스: 켜짐

## 비고
- 각 pane은 `openclaw tui --session <key>`로 독립 세션 맥락 유지.
- webchat 단일창보다 맥락 분리가 확실함.

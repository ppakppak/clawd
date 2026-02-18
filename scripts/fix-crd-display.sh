#!/bin/bash
# Chrome Remote Desktop이 물리 디스플레이에 붙도록 설정

# 현재 물리 디스플레이 번호 찾기
PHYSICAL_DISPLAY=$(who | grep "(:.*)" | grep -oP ":\d+" | head -1 | tr -d ':')

if [ -z "$PHYSICAL_DISPLAY" ]; then
    echo "물리 디스플레이를 찾을 수 없습니다"
    exit 1
fi

echo "물리 디스플레이: :$PHYSICAL_DISPLAY"

CRD_SCRIPT="/opt/google/chrome-remote-desktop/chrome-remote-desktop"

# 현재 설정값 확인
CURRENT=$(grep "FIRST_X_DISPLAY_NUMBER = " "$CRD_SCRIPT" | head -1)
echo "현재 설정: $CURRENT"

# 변경 필요한지 확인
if echo "$CURRENT" | grep -q "= $PHYSICAL_DISPLAY"; then
    echo "이미 올바른 값입니다. 변경 불필요."
    exit 0
fi

# 변경
sudo sed -i "s/FIRST_X_DISPLAY_NUMBER = [0-9]*/FIRST_X_DISPLAY_NUMBER = $PHYSICAL_DISPLAY/" "$CRD_SCRIPT"

# 확인
NEW=$(grep "FIRST_X_DISPLAY_NUMBER = " "$CRD_SCRIPT" | head -1)
echo "변경 후: $NEW"

# Chrome Remote Desktop 재시작
echo "Chrome Remote Desktop 재시작 중..."
sudo systemctl restart chrome-remote-desktop@$USER 2>/dev/null || \
    /opt/google/chrome-remote-desktop/chrome-remote-desktop --stop && \
    /opt/google/chrome-remote-desktop/chrome-remote-desktop --start

echo "완료!"

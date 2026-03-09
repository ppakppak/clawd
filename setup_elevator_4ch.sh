#!/usr/bin/env bash
set -euo pipefail

UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
mkdir -p "$HOME/projects/elevator/logs"
mkdir -p "$HOME/projects/elevator/deepstream_pose/logs"

RTSP_URL='rtsp://ppakppak:2z!pslave@192.168.0.72:554/stream2'
VIDEO1='/home/ppak/projects/elevator/elve1.mp4'
VIDEO2='/home/ppak/projects/elevator/elve2.mp4'

# 기존 단일 서비스는 비활성화 (4채널 구성으로 전환)
systemctl --user disable --now elevator.service >/dev/null 2>&1 || true
systemctl --user disable --now elevator-preview.service >/dev/null 2>&1 || true

write_ds_unit () {
  local name="$1"
  local source="$2"
  cat > "$UNIT_DIR/$name" <<EOF
[Unit]
Description=Elevator DeepStream channel: $name
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/ppak/projects/elevator/deepstream_pose
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 /home/ppak/projects/elevator/deepstream_pose/deepstream_pose_simple.py --source $source --no-display
Restart=always
RestartSec=3
StandardOutput=append:/home/ppak/projects/elevator/deepstream_pose/logs/${name%.service}.out.log
StandardError=append:/home/ppak/projects/elevator/deepstream_pose/logs/${name%.service}.err.log

[Install]
WantedBy=default.target
EOF
}

write_preview_unit () {
  local name="$1"
  local source="$2"
  local port="$3"
  cat > "$UNIT_DIR/$name" <<EOF
[Unit]
Description=Elevator preview channel: $name
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/ppak/projects/elevator
Environment=PYTHONUNBUFFERED=1
Environment=OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;udp|fflags;nobuffer|flags;low_delay|max_delay;500000|reorder_queue_size;0
ExecStart=/home/ppak/projects/elevator/venv/bin/python /home/ppak/projects/elevator/preview_server.py --source $source --port $port --width 640 --jpeg-quality 65
Restart=always
RestartSec=3
StandardOutput=append:/home/ppak/projects/elevator/logs/${name%.service}.out.log
StandardError=append:/home/ppak/projects/elevator/logs/${name%.service}.err.log

[Install]
WantedBy=default.target
EOF
}

# DeepStream 4채널
write_ds_unit "elevator-ds-webcam.service" "0"
write_ds_unit "elevator-ds-rtsp.service" "$RTSP_URL"
write_ds_unit "elevator-ds-video1.service" "$VIDEO1"
write_ds_unit "elevator-ds-video2.service" "$VIDEO2"

# Preview 4채널 (포트 분리)
write_preview_unit "elevator-preview-webcam.service" "0" "5000"
write_preview_unit "elevator-preview-rtsp.service" "$RTSP_URL" "5001"
write_preview_unit "elevator-preview-video1.service" "$VIDEO1" "5002"
write_preview_unit "elevator-preview-video2.service" "$VIDEO2" "5003"

systemctl --user daemon-reload

for svc in \
  elevator-ds-webcam.service \
  elevator-ds-rtsp.service \
  elevator-ds-video1.service \
  elevator-ds-video2.service \
  elevator-preview-webcam.service \
  elevator-preview-rtsp.service \
  elevator-preview-video1.service \
  elevator-preview-video2.service
  do
    systemctl --user enable --now "$svc" >/dev/null 2>&1 || true
  done

sleep 4

echo "=== ACTIVE SERVICES ==="
for svc in \
  elevator-ds-webcam.service \
  elevator-ds-rtsp.service \
  elevator-ds-video1.service \
  elevator-ds-video2.service \
  elevator-preview-webcam.service \
  elevator-preview-rtsp.service \
  elevator-preview-video1.service \
  elevator-preview-video2.service
  do
    state=$(systemctl --user is-active "$svc" 2>/dev/null || true)
    enabled=$(systemctl --user is-enabled "$svc" 2>/dev/null || true)
    echo "$svc : active=$state enabled=$enabled"
  done

echo "=== PORT CHECK ==="
ss -ltn | egrep ':5000|:5001|:5002|:5003' || true

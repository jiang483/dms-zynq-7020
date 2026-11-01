#!/bin/bash
# board_reverify_cleanroom.sh -- verify the artifact built from the clean-room
# reproduction, on the board. MUST run as root (Jupyter root terminal):
# PYNQ Overlay needs /dev/mem, and plain ssh has no passwordless sudo.
#
#   cd /home/xilinx/jupyter_notebooks/PYNQ/src
#   bash board_reverify_cleanroom.sh
#
# Writes /tmp/board_reverify_cleanroom.log (readable by the xilinx user).

LOG=/tmp/board_reverify_cleanroom.log
exec > >(tee "$LOG") 2>&1

echo "=== board reverify (clean-room build) ==="
date
echo "--- artifact under test ---"
md5sum /home/xilinx/jupyter_notebooks/PYNQ/design_1.bit \
       /home/xilinx/jupyter_notebooks/PYNQ/design_1.hwh
ls -la /home/xilinx/jupyter_notebooks/PYNQ/design_1.bit \
       /home/xilinx/jupyter_notebooks/PYNQ/design_1.hwh

cd /home/xilinx/jupyter_notebooks/PYNQ/src || exit 1

for t in tests/test_eye_cnn.py tests/test_img_preproc.py tests/test_context_cnn_hw.py; do
    echo
    echo "===== $t --hw ====="
    timeout 600 bash run.sh "$t" --hw
    echo "EXIT_$t=$?"
done

echo
echo "===== demo smoke: 90 frames, context on ====="
timeout 240 bash run.sh demo_eye_perclos.py \
    --osd --classifier cnn --osd-native-haar \
    --face-detect-scale 2 --face-stride 8 --face-fallback \
    --context --context-stride 5 \
    --frames 90 --interval 0.1
echo "DEMO_EXIT=$?"

echo
echo "=== context dump tail (if camera saw a face) ==="
ls -la snapshots/context_log.csv 2>/dev/null
tail -5 snapshots/context_log.csv 2>/dev/null
chmod 644 "$LOG" 2>/dev/null
echo "=== DONE $(date) ==="

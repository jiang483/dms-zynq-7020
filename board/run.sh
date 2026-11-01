#!/bin/bash
# Wrapper: run python inside the PYNQ login environment.
#
# `ssh host 'cmd'` is a NON-login, NON-interactive shell, so /etc/profile.d/*
# is never sourced. That skips pynq_venv.sh (-> "No module named 'pynq'") and
# xrt_setup.sh (-> "No Devices Found" when loading an Overlay). Jupyter gets
# both automatically, which is why things work there but not over plain ssh.
#
# Usage:  ./run.sh debug_segfault.py --stage a --iters 10

source /etc/profile.d/pynq_venv.sh
source /etc/profile.d/xrt_setup.sh

cd /home/xilinx/jupyter_notebooks/PYNQ/src || exit 1
exec python3 -u "$@"

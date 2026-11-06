#!/usr/bin/env bash
# Runs every hardware-free simulation test. Needs only python3, numpy and pillow.
set -e
cd "$(dirname "$0")"
python3 -m py_compile ../glowbox/*.py
echo "### analysis";        python3 test_analysis.py
echo "### main program";    python3 sim_main.py > /dev/null && echo ok
echo "### bench tool";      python3 sim_bench.py > /dev/null && echo ok
echo "### system test";     python3 sim_system_test.py > /dev/null && echo ok
for a in "" broken rgb lag6; do
  echo "### camera test $a"; python3 sim_camera_test.py $a | tail -2 | head -1
done
echo "ALL SIMULATIONS RAN"

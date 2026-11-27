#!/bin/bash
# Round 1a-5: tally Sonnet the way Haiku was tallied (no model calls). Keeps Haiku's worksheet and quotecheck aside.
set -u
# SP is the session's scratch folder (not kept); S holds the score files and these scripts.
M=/var/tmp/tuesday-measure/1a5; SP=${SP:?set SP to the scratch folder}
S=$SP/l1a5/score; W=$M-pins/candidate
cd "$W" || exit 1
for a in alone tuesday; do for p in 1 2; do
  PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -B evals/compare_arms.py $M/runs/sonnet/$a/part-$p $M/baseline/sonnet/$a/part-$p \
    --checks-from $M/runs/sonnet/$a/part-$p $M/checkrun/sonnet/$a/part-$p > $S/compare-sonnet-$a-part-$p.txt 2>&1; echo "compare $a $p rc=$?"
done; done
timeout 300 python3 -I -B $M/frozen/scorers/score_item.py $W $SP/fixround/round sonnet=$M/runs/sonnet/tuesday/part-1,$M/runs/sonnet/alone/part-1 > $S/item-sonnet.txt 2>&1; echo "item rc=$?"
cd "$S" || exit 1
timeout 300 python3 -I -B locate_account_email.py $M haiku sonnet > located-account-email.json 2>loc.err; echo "loc rc=$?"
timeout 600 python3 -I -B score_1a.py $M sonnet --json sonnet-score.json > sonnet-score.txt 2>&1; echo "score rc=$?"
[ -f worksheet-haiku.md ] || cp worksheet.md worksheet-haiku.md
[ -f quotecheck-haiku.jsonl ] || cp quotecheck.jsonl quotecheck-haiku.jsonl
timeout 600 python3 -I -B worksheet.py $M $S $S/worksheet.md > ws.log 2>&1; echo "ws rc=$?"; tail -2 ws.log
timeout 600 python3 -I -B quotecheck.py $M $S $S/quotecheck.jsonl > qc.log 2>&1; echo "qc rc=$?"; tail -4 qc.log
timeout 300 python3 -I -B reference_reads.py $M sonnet > refs-sonnet.txt 2>&1; echo "refs rc=$?"
timeout 300 python3 -I -B nudges.py $M sonnet > nudges-sonnet.txt 2>&1; echo "nudges rc=$?"
timeout 300 python3 -I -B e23_gates.py $M haiku sonnet > e23.txt 2>&1; echo "e23 rc=$?"
timeout 300 python3 -I -B core_after_adj.py $M haiku sonnet > core-after-adj.txt 2>&1; echo "core rc=$?"

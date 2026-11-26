#!/bin/bash
# Round 1a-6: tally one model the way rounds 1a-4 and 1a-5 were tallied (no model calls), then refresh the files that
# cover every scored model. Usage: SP=<scratch folder> tally_model.sh MODEL [MODEL_SO_FAR...]
set -u
MODEL=$1; shift; ALL="$*"
M=/var/tmp/tuesday-measure/1a6; SP=${SP:?set SP to the scratch folder}
S=$SP/l1a6/score; W=$M-pins/candidate
cd "$W" || exit 1
for a in alone tuesday; do for p in 1 2; do
  PYTHONDONTWRITEBYTECODE=1 timeout 300 python3 -B evals/compare_arms.py $M/runs/$MODEL/$a/part-$p $M/baseline/$MODEL/$a/part-$p \
    --checks-from $M/runs/$MODEL/$a/part-$p $M/checkrun/$MODEL/$a/part-$p > $S/compare-$MODEL-$a-part-$p.txt 2>&1; echo "compare $a $p rc=$?"
done; done
timeout 300 python3 -I -B $M/frozen/scorers/score_item.py $W $SP/fixround/round $MODEL=$M/runs/$MODEL/tuesday/part-1,$M/runs/$MODEL/alone/part-1 > $S/item-$MODEL.txt 2>&1; echo "item rc=$?"
cd "$S" || exit 1
timeout 600 python3 -I -B score_1a.py $M $MODEL --json $MODEL-score.json > $MODEL-score.txt 2>&1; echo "score rc=$?"
timeout 300 python3 -I -B locate_account_email.py $M $ALL > located-account-email.json 2>loc.err; echo "loc rc=$?"
timeout 600 python3 -I -B worksheet.py $M $S $S/worksheet.md > ws.log 2>&1; echo "ws rc=$?"; tail -1 ws.log
timeout 600 python3 -I -B quotecheck.py $M $S $S/quotecheck.jsonl > qc.log 2>&1; echo "qc rc=$?"; tail -4 qc.log
timeout 300 python3 -I -B reference_reads.py $M $MODEL > refs-$MODEL.txt 2>&1; echo "refs rc=$?"
timeout 300 python3 -I -B nudges.py $M $MODEL > nudges-$MODEL.txt 2>&1; echo "nudges rc=$?"
timeout 300 python3 -I -B e23_gates.py $M $ALL > e23.txt 2>&1; echo "e23 rc=$?"

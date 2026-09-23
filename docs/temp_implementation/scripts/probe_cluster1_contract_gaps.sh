#!/usr/bin/env bash
# Probes de contrato do Cluster 1 (R2/R5) — achados G1..G5 do Handoff 003.
# Roda apenas em fixtures descartáveis sob mktemp; nunca executa push.
# Uso: bash docs/temp_implementation/scripts/probe_cluster1_contract_gaps.sh
set -u

CEH_REPO="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
GATE="$CEH_REPO/clearer-engineering/scripts/safety-gate.py"
RUNNER="$CEH_REPO/clearer-engineering/scripts/test-runner.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "CEH_HEAD=$(git -C "$CEH_REPO" rev-parse HEAD)"
echo "CEH_DIRTY_FILES=$(git -C "$CEH_REPO" status --porcelain --untracked-files=no | wc -l)"
echo "HOST=$(uname -srm) PYTHON=$(python3 --version 2>&1)"
echo

decision() {
    python3 "$GATE" --check "$1" --env "${2:-development}" \
        | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['decision'], '|', d.get('use_case'))"
}

write_test() {
    printf 'import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(1, %s)\n' "$1" > tests/test_a.py
}

cd "$TMP"
git init -qb dev
git config user.name "CEH Probe"
git config user.email "ceh-probe@example.invalid"
mkdir -p .github/workflows tests
printf 'on: push\njobs:\n  t:\n    runs-on: x\n    steps:\n      - run: python3 -m unittest\n' > .github/workflows/ci.yml
touch tests/__init__.py requirements.txt
write_test 1
git add .
git commit -qm "fixture: suíte verde"

echo "G1) Certificado escrito à mão, sem rodar testes:"
mkdir -p .ceh
printf '{"commit_hash":"%s","status":"PASS","exit_code":0,"canonical_verified":true,"command":"python3 -m unittest"}\n' \
    "$(git rev-parse HEAD)" > .ceh/last-ci-run.json
echo "  gate: $(decision 'git push origin dev')"
rm -rf .ceh

echo "G2) HEAD com teste quebrado + correção apenas no worktree:"
write_test 2
git commit -qam "fixture: HEAD quebrado"
write_test 1
bash "$RUNNER" python3 -m unittest >/dev/null 2>&1
echo "  runner_exit=$? cert_commit=$(python3 -c "import json; print(json.load(open('.ceh/last-ci-run.json'))['commit_hash'][:8])") head=$(git rev-parse --short=8 HEAD) arquivos_sujos=$(git status --porcelain --untracked-files=no | wc -l)"
echo "  gate: $(decision 'git push origin dev')"
git checkout -q tests/test_a.py
rm -rf .ceh

echo "G3) Sem certificado, variantes de force push em development:"
for c in 'git push origin dev' 'git push -f origin dev' 'git push --force-with-lease origin dev' 'git push origin +dev'; do
    printf '  %-42s gate: %s\n' "$c" "$(decision "$c")"
done

echo "G4) Certificado com aspas no comando executado:"
bash "$RUNNER" python3 -c 'print("x")' >/dev/null 2>&1
printf '  json.load: '
python3 -c "import json; json.load(open('.ceh/last-ci-run.json')); print('OK')" 2>&1 | tail -1
rm -rf .ceh

echo "G5) Flags de interpretador fora da denylist (package.json):"
git checkout -q -b g5
printf 'on: push\njobs:\n  t:\n    runs-on: x\n    steps:\n      - run: npm test\n' > .github/workflows/ci.yml
python3 -c "import json; json.dump({'scripts': {'test': \"python3 -Ic 'exit(0)'\"}}, open('package.json', 'w'))"
git add -A
git commit -qm "fixture: test fake"
bash "$RUNNER" >/dev/null 2>&1
echo "  runner_exit=$? canonical_verified=$(python3 -c "import json; print(json.load(open('.ceh/last-ci-run.json'))['canonical_verified'])")"
echo "  gate: $(decision 'git push origin g5')"

#!/usr/bin/env python3
"""
test_rm_fuzz.py - Teste de propriedade baseado em Fuzzing com 2000+ casos (PR-04d).
Usa random.Random com seed fixa determinística (20260926) e stdlib apenas.
Verifica duas invariantes matemáticas inegociáveis:
1. Invariante 1: Se a decisão for FILESYSTEM_SAFE, o alvo resolvido deve obrigatoriamente
   estar sob /tmp/, ou ser arquivo único com extensão no cwd, ou seu relpath normalizado
   contra o cwd não pode começar com '..' e seu primeiro segmento DEVE pertencer a safe_roots.
2. Invariante 2: Se o alvo normalizado for '/', um SYSTEM_ROOT, o HOME, '/home/<x>',
   ou um ancestral ou o próprio diretório de trabalho (cwd), a decisão DEVE ser 'deny CATASTROPHIC'
   em qualquer ambiente.
"""
from __future__ import annotations

import os
import random
import sys
import unittest
from pathlib import Path
from importlib import import_module

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

safety_gate = import_module("safety-gate")
evaluate_command = safety_gate.evaluate_command

rm_mod = import_module("ceh_core.rm")
SYSTEM_ROOTS = rm_mod.SYSTEM_ROOTS


class TestRmFuzz(unittest.TestCase):
    """Teste de propriedade com fuzzing determinístico cobrindo ≥ 2000 variantes de caminhos."""

    def test_rm_path_fuzz_invariants(self):
        rng = random.Random(20260926)
        cwd = Path("/home/user/workspace/project").resolve()
        cwd_str = str(cwd)
        home_dir = "/home/user"

        safe_prefixes = ["dist", "build", "coverage", "scratch", ".tmp", "tmp", "node_modules/.cache"]
        unsafe_prefixes = ["src", "app", ".git", "etc", "var", "bin", "home", "usr", "opt"]
        special_tokens = [".", "..", "...", "/", "//", "///", "./", "../", "../..", "../../.."]
        names = ["foo", "bar", "test", "assets", "cache", "model", "index.js", "a.txt", "script.py", "*"]
        connectors = ["/", "//", "/./", "/../"]

        safe_roots = {"tmp", ".tmp", "scratch", ".cache", "dist", "build", "coverage"}

        iterations = 2500
        tested_cases = 0

        for i in range(iterations):
            # Gera alvos diversos combinando tokens
            depth = rng.randint(1, 4)
            components = []
            is_abs = rng.random() < 0.3

            for _ in range(depth):
                pool = []
                r = rng.random()
                if r < 0.25:
                    pool = safe_prefixes
                elif r < 0.50:
                    pool = unsafe_prefixes
                elif r < 0.75:
                    pool = special_tokens
                else:
                    pool = names
                components.append(rng.choice(pool))

            sep = rng.choice(connectors)
            raw_path = sep.join(components)
            if is_abs:
                raw_path = "/" + raw_path

            # Variações com flags
            flags = rng.choice(["-rf", "-r -f", "--recursive --force", "-f", "-r"])
            cmd = f"rm {flags} {raw_path}"

            env = rng.choice(["development", "staging", "production"])

            decision, reason, _, use_case = evaluate_command(cmd, explicit_env=env, base_cwd=cwd)
            tested_cases += 1

            # Normalização de referência
            clean_target = raw_path.replace('"', "").replace("'", "").strip()
            clean_target = clean_target.replace("${PWD}", cwd_str).replace("$PWD", cwd_str)
            clean_target = clean_target.replace("${HOME}", home_dir).replace("$HOME", home_dir)

            # Normalização para Invariante 1
            norm_safe = os.path.normpath(clean_target if os.path.isabs(clean_target) else os.path.join(cwd_str, clean_target))

            # Normalização para Invariante 2 (catastrófico olha diretório base de glob /*)
            base_cat = clean_target
            if base_cat.endswith("/*"):
                base_cat = base_cat[:-2] or "/"
            elif base_cat.endswith("/*/"):
                base_cat = base_cat[:-3] or "/"
            norm_cat = os.path.normpath(base_cat if os.path.isabs(base_cat) else os.path.join(cwd_str, base_cat))

            # INVARIANTE 2: Catastrófico
            is_actually_catastrophic = False
            if norm_cat == "/":
                is_actually_catastrophic = True
            elif norm_cat in SYSTEM_ROOTS:
                is_actually_catastrophic = True
            elif norm_cat == home_dir or (norm_cat.startswith("/home/") and norm_cat.count("/") == 2):
                is_actually_catastrophic = True
            elif norm_cat == cwd_str or cwd_str.startswith(norm_cat + "/"):
                is_actually_catastrophic = True

            if is_actually_catastrophic:
                self.assertEqual(
                    decision, "deny",
                    f"[INVARIANTE 2 VIOLADA] Alvo catastrófico '{raw_path}' (norm: '{norm_cat}') obteve '{decision}' em env '{env}'. Cmd: {cmd}"
                )
                self.assertEqual(
                    use_case, "CATASTROPHIC",
                    f"[INVARIANTE 2 VIOLADA] Alvo catastrófico '{raw_path}' (norm: '{norm_cat}') obteve use_case '{use_case}'. Cmd: {cmd}"
                )

            # INVARIANTE 1: Limpeza segura (FILESYSTEM_SAFE)
            if use_case == "FILESYSTEM_SAFE":
                self.assertEqual(decision, "allow", f"[INVARIANTE 1 VIOLADA] FILESYSTEM_SAFE deve ser allow: {cmd}")
                
                # Deve ser sob /tmp/ ou no cwd
                if norm_safe == "/tmp" or norm_safe.startswith("/tmp/"):
                    pass
                else:
                    self.assertTrue(
                        norm_safe == cwd_str or norm_safe.startswith(cwd_str + "/"),
                        f"[INVARIANTE 1 VIOLADA] FILESYSTEM_SAFE fora do cwd e fora de /tmp/: '{raw_path}' (norm: '{norm_safe}')"
                    )
                    rel = os.path.relpath(norm_safe, cwd_str)
                    self.assertFalse(
                        rel.startswith("..") or rel == ".",
                        f"[INVARIANTE 1 VIOLADA] FILESYSTEM_SAFE relpath inválido '{rel}' para '{raw_path}'"
                    )
                    parts = rel.split(os.sep)
                    first_seg = parts[0]
                    last_seg = parts[-1]
                    # Primeiro segmento em safe_roots ou storage/framework/cache ou node_modules/.cache
                    is_valid_safe = (first_seg in safe_roots) or rel.startswith("storage/framework/cache") or rel.startswith("node_modules/.cache")
                    # Ou arquivo único com extensão dentro do cwd sob -f
                    is_valid_file = ("." in last_seg and not last_seg.startswith(".") and "*" not in last_seg and not rel.endswith("/"))
                    self.assertTrue(
                        is_valid_safe or is_valid_file,
                        f"[INVARIANTE 1 VIOLADA] FILESYSTEM_SAFE com primeiro segmento inseguro: '{first_seg}' (rel: '{rel}', raw: '{raw_path}')"
                    )

        print(f"✔ Fuzz Test Concluído com Sucesso: {tested_cases} casos verificados contra Invariantes 1 e 2.")


if __name__ == "__main__":
    unittest.main()

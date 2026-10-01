#!/usr/bin/env python3
"""
rc_aliases.py — Canonical shell rc alias manager for CLEARER Engineering Harness (CEH).
Single source of truth for installing, updating, and safely removing CEH shell aliases.
Strictly adheres to ADR 007 and eliminates unsafe heuristics.
"""

import sys
import os
import re

START_MARKER = "# BEGIN CLEARER ENGINEERING HARNESS (CEH) ALIASES"
END_MARKER = "# END CLEARER ENGINEERING HARNESS (CEH) ALIASES"
LEGACY_HEADER_REGEX = r"# === CLEARER Engineering Harness \(CEH\) ===\n?"

DEFAULT_KNOWN_NAMES = {
    'agy-ceh', 'agy-ceh-yolo', 'ceh', 'ceh-env', 'ceh-branches',
    'ceh-preflight', 'ceh-evals', 'ceh-monitor', 'ceh-doc-audit',
    'ceh-conselho', 'ceh-help'
}


def load_canonical_aliases(alias_conf_path):
    """Loads exact CEH alias definitions and known alias names from aliases.sh."""
    exact_ceh_lines = set()
    known_names = set(DEFAULT_KNOWN_NAMES)
    if alias_conf_path and os.path.isfile(alias_conf_path):
        try:
            with open(alias_conf_path, 'r', encoding='utf-8') as af:
                for line in af:
                    l_str = line.strip()
                    if l_str.startswith('alias '):
                        exact_ceh_lines.add(l_str)
                        am = re.match(r'^alias\s+([a-zA-Z0-9_-]+)=', l_str)
                        if am:
                            known_names.add(am.group(1))
        except Exception as e:
            sys.stderr.write(f"Erro ao ler alias_conf {alias_conf_path}: {e}\n")
            sys.exit(1)
    return exact_ceh_lines, known_names


def remove_orphan_aliases(content, alias_conf_path):
    """
    Safely removes unblocked orphan CEH aliases.
    Strictly anchored at line start (^alias <name>=).
    Only removes if the line matches an exact canonical alias or carries CEH signatures:
      - 'plugins/clearer-engineering/'
      - '--agent clearer-harness'
    User-defined aliases and comments are strictly preserved byte-by-byte.
    """
    exact_ceh_lines, known_names = load_canonical_aliases(alias_conf_path)
    lines = content.splitlines(keepends=True)
    filtered = []
    for line in lines:
        stripped = line.strip()
        is_ceh_orphan = False
        m_alias = re.match(r'^alias\s+([a-zA-Z0-9_-]+)=(.*)$', line)
        if m_alias:
            name = m_alias.group(1)
            val = m_alias.group(2)
            if name in known_names:
                if (stripped in exact_ceh_lines or
                    'plugins/clearer-engineering/' in val or
                    '--agent clearer-harness' in val):
                    is_ceh_orphan = True
        if not is_ceh_orphan:
            filtered.append(line)
    return "".join(filtered)


def find_line_anchored(text: str, marker: str, start: int = 0) -> int:
    pos = start
    while True:
        idx = text.find(marker, pos)
        if idx == -1:
            return -1
        is_line_start = (idx == 0 or text[idx - 1] == '\n')
        after_idx = idx + len(marker)
        is_line_end = (after_idx >= len(text) or text[after_idx] in ('\n', '\r'))
        if is_line_start and is_line_end:
            return idx
        pos = idx + 1


def remove_ceh_block(content):
    """
    Removes the bounded CEH marker block.
    AN1 fix: Counts consecutive preceding newlines and only removes min(num_newlines, prefix_len).
    Never removes user configuration characters outside the block.
    F12: Marcadores ancorados a linhas completas para evitar apagar linhas com strings.
    """
    start_idx = find_line_anchored(content, START_MARKER)
    if start_idx == -1:
        return content

    end_idx = find_line_anchored(content, END_MARKER, start_idx + len(START_MARKER))
    if end_idx == -1:
        return content

    end_of_block = end_idx + len(END_MARKER)
    if end_of_block < len(content) and content[end_of_block] == '\n':
        end_of_block += 1

    block_text = content[start_idx:end_of_block]
    m_p = re.search(r'# CEH_RC_PREFIX_LEN:\s*(\d+)', block_text)
    prefix_len = int(m_p.group(1)) if m_p else 0

    # Count consecutive preceding newlines immediately before start_idx
    actual_preceding_newlines = 0
    i = start_idx - 1
    while i >= 0 and content[i] == '\n':
        actual_preceding_newlines += 1
        i -= 1

    newlines_to_remove = min(actual_preceding_newlines, prefix_len)
    remove_start = start_idx - newlines_to_remove

    return content[:remove_start] + content[end_of_block:]


def clean_rc_content(content, alias_conf_path):
    """Performs full cleanup: bounded block, legacy headers, and legitimate orphan aliases."""
    content = remove_ceh_block(content)
    content = re.sub(LEGACY_HEADER_REGEX, '', content)
    content = remove_orphan_aliases(content, alias_conf_path)
    return content


def install_rc_content(content, alias_conf_path, aliases_body):
    """
    Installs or updates CEH alias block with idempotency and safe prefix tracking.
    """
    aliases_body = aliases_body.strip()
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}\n(?:# CEH_RC_PREFIX_LEN:\s*(\d+)\n)?.*?{re.escape(END_MARKER)}\n?",
        re.DOTALL
    )

    # Remove legacy headers if present (AP1)
    content = re.sub(LEGACY_HEADER_REGEX, '', content)

    m = pattern.search(content)
    if m:
        p_len = m.group(1) if m.group(1) is not None else 0
        block = f"{START_MARKER}\n# CEH_RC_PREFIX_LEN: {p_len}\n{aliases_body}\n{END_MARKER}\n"
        return pattern.sub(lambda _: block, content)

    # First clean any unblocked orphan aliases without removing user configs
    content = remove_orphan_aliases(content, alias_conf_path)

    # Determine prefix safely
    prefix = ""
    prefix_len = 0
    if content:
        if content.endswith("\n\n"):
            prefix = ""
            prefix_len = 0
        elif content.endswith("\n"):
            prefix = "\n"
            prefix_len = 1
        else:
            prefix = "\n\n"
            prefix_len = 2

    block = f"{START_MARKER}\n# CEH_RC_PREFIX_LEN: {prefix_len}\n{aliases_body}\n{END_MARKER}\n"
    return content + prefix + block


def main():
    if len(sys.argv) < 3:
        sys.stderr.write("Uso: rc_aliases.py <clean-rc|install-rc> <rc_path> <alias_conf_path> [aliases_body]\n")
        sys.exit(1)

    action = sys.argv[1]
    rc_path = sys.argv[2]
    alias_conf_path = sys.argv[3] if len(sys.argv) > 3 else ""

    if not os.path.exists(rc_path):
        return

    try:
        with open(rc_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        sys.stderr.write(f"Erro ao ler {rc_path}: {e}\n")
        sys.exit(1)

    if action == "clean-rc":
        updated = clean_rc_content(content, alias_conf_path)
    elif action == "install-rc":
        if len(sys.argv) < 5:
            sys.stderr.write("Erro: aliases_body é obrigatório para install-rc\n")
            sys.exit(1)
        aliases_body = sys.argv[4]
        updated = install_rc_content(content, alias_conf_path, aliases_body)
    else:
        sys.stderr.write(f"Ação desconhecida: {action}\n")
        sys.exit(1)

    try:
        with open(rc_path, 'w', encoding='utf-8') as f:
            f.write(updated)
    except Exception as e:
        sys.stderr.write(f"Erro ao escrever em {rc_path}: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

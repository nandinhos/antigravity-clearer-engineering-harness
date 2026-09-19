#!/usr/bin/env bash
# ==============================================================================
# task-monitor.sh - CEH Real-Time Task & Background Process Monitor
# ==============================================================================
# Cadência de Heartbeat: 25 segundos (Anti-Idle UX)
# ==============================================================================
set -u

INTERVAL=25
EXPORT_PATH=""
ONCE=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --live|-l)
            ONCE=false
            shift
            ;;
        --interval|-i)
            INTERVAL="$2"
            shift 2
            ;;
        --export|-e)
            EXPORT_PATH="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

render_monitor() {
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║        🛰️  CEH Live Task Monitor — Heartbeat (${INTERVAL}s)               ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo "Timestamp: $timestamp"
    echo "Diretório: $(pwd)"
    echo "---------------------------------------------------------------------"

    # Encontrar processos ativos de teste / build / harness
    local active_procs
    active_procs=$(ps -eo pid,etime,args | grep -E "(artisan test|pest|phpunit|pytest|npm test|pnpm test|yarn test|cargo test|go test|safety-gate|diff-audit)" | grep -v "grep" | grep -v "task-monitor" || true)

    if [[ -z "$active_procs" ]]; then
        echo "Status: 🟢 OCIOSO (Nenhum processo pesado em background)"
        echo ""
    else
        echo "Status: 🟡 EM EXECUÇÃO (Comandos ativos em segundo plano)"
        echo ""
        printf "%-8s %-12s %-45s\n" "PID" "TEMPO" "COMANDO"
        echo "---------------------------------------------------------------------"
        while IFS= read -r line; do
            local pid etime cmd
            pid=$(echo "$line" | awk '{print $1}')
            etime=$(echo "$line" | awk '{print $2}')
            cmd=$(echo "$line" | cut -d' ' -f3- | cut -c1-45)
            printf "%-8s %-12s %-45s\n" "$pid" "$etime" "$cmd"
        done <<< "$active_procs"
        echo ""
    fi

    # Se exportar para markdown
    if [[ -n "$EXPORT_PATH" ]]; then
        cat << EOF > "$EXPORT_PATH"
# 🛰️ CEH Live Task Monitor
**Última Atualização:** \`$timestamp\` | **Cadência:** \`${INTERVAL}s\`

| PID | Tempo Decorrido | Comando | Status |
|---|---|---|---|
EOF
        if [[ -z "$active_procs" ]]; then
            echo "| - | - | Nenhum comando em execução | 🟢 IDLE |" >> "$EXPORT_PATH"
        else
            while IFS= read -r line; do
                local pid etime cmd
                pid=$(echo "$line" | awk '{print $1}')
                etime=$(echo "$line" | awk '{print $2}')
                cmd=$(echo "$line" | cut -d' ' -f3-)
                echo "| \`$pid\` | \`$etime\` | \`$cmd\` | 🟡 RUNNING |" >> "$EXPORT_PATH"
            done <<< "$active_procs"
        fi
    fi
}

if [[ "$ONCE" = true ]]; then
    render_monitor
else
    while true; do
        clear 2>/dev/null || true
        render_monitor
        sleep "$INTERVAL"
    done
fi

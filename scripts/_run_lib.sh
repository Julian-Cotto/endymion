#!/usr/bin/env bash
# Shared launcher helpers. Source from a runner script.
# Caller must define:
#   SVC_NAMES=(name1 name2 ...)         # service ids (unique, used for log file + tail prefix)
#   declare -A SVC_DIR                  # name -> working dir
#   declare -A SVC_CMD                  # name -> bash command to exec inside the dir
#   declare -A SVC_HEALTH               # name -> URL to curl until 2xx (optional)
#   declare -A SVC_HEALTH_TIMEOUT       # name -> seconds (optional, default 60)
#   declare -A SVC_BOOTSTRAP            # name -> "python:<reqfile>" or "node" (optional)
#   declare -A SVC_ENV_FROM_EXAMPLE     # name -> 1 to copy .env.example -> .env if missing (optional)
#   PORTS=(...)                          # ports to clear before launch
#   LOG_DIR                              # where to write per-service logs

set -u

PIDS=()

cleanup() {
  echo
  echo "[run] shutting down..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      pkill -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true
    fi
  done
  sleep 1
  for pid in "${PIDS[@]}"; do
    kill -9 "$pid" 2>/dev/null || true
  done
  exit 0
}
trap cleanup INT TERM

clear_ports() {
  local cleared=0
  for p in "$@"; do
    local pids
    pids="$(ss -tlnpH "sport = :$p" 2>/dev/null \
      | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)"
    if [[ -z "$pids" ]] && command -v lsof >/dev/null 2>&1; then
      pids="$(lsof -ti tcp:$p 2>/dev/null | sort -u)"
    fi
    if [[ -n "$pids" ]]; then
      echo "[run] port $p in use by pid(s) $pids — killing"
      # shellcheck disable=SC2086
      kill $pids 2>/dev/null || true
      cleared=1
    fi
  done
  if [[ $cleared -eq 1 ]]; then
    sleep 1
    for p in "$@"; do
      local pids
      pids="$(ss -tlnpH "sport = :$p" 2>/dev/null \
        | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u)"
      if [[ -n "$pids" ]]; then
        echo "[run] port $p still held — kill -9 $pids"
        # shellcheck disable=SC2086
        kill -9 $pids 2>/dev/null || true
      fi
    done
  fi
}

color_for() {
  case "$1" in
    registry)   printf '\033[36m' ;;  # cyan
    bootstrap)  printf '\033[33m' ;;  # yellow
    shell)      printf '\033[35m' ;;  # magenta
    inv-api)    printf '\033[32m' ;;  # green
    inv-web)    printf '\033[34m' ;;  # blue
    *)          printf '\033[37m' ;;
  esac
}
RST='\033[0m'

ensure_python_venv() {
  local dir="$1" req="${2:-requirements.txt}"
  if [[ ! -d "$dir/.venv" ]]; then
    echo "[run] creating venv: $dir/.venv"
    python3 -m venv "$dir/.venv"
  fi
  if [[ "${BOOTSTRAP:-1}" == "1" ]]; then
    ( cd "$dir" && source .venv/bin/activate && pip install -q -r "$req" )
  fi
}

ensure_node_install() {
  local dir="$1"
  if [[ "${BOOTSTRAP:-1}" == "1" && ! -d "$dir/node_modules" ]]; then
    echo "[run] npm install: $dir"
    ( cd "$dir" && npm install --silent --no-audit --no-fund )
  fi
}

start_bg() {
  local name="$1" dir="$2" cmd="$3"
  local logf="$LOG_DIR/${name}.log"
  : > "$logf"
  echo "[run] starting $name ($dir)"
  ( cd "$dir" && bash -c "$cmd" ) >>"$logf" 2>&1 &
  local pid=$!
  PIDS+=("$pid")
  echo "[run] $name pid=$pid log=$logf"
}

wait_health() {
  local name="$1" url="$2" timeout="${3:-60}" elapsed=0
  while ! curl -fsS -o /dev/null "$url"; do
    sleep 2
    elapsed=$((elapsed+2))
    if [[ $elapsed -ge $timeout ]]; then
      echo "[run] WARNING: $name not healthy at $url after ${timeout}s — continuing"
      return 0
    fi
  done
  echo "[run] $name healthy ($url)"
}

# Launch every service in SVC_NAMES order; do bootstrap, env-copy, health waits.
launch_services() {
  for name in "${SVC_NAMES[@]}"; do
    local dir="${SVC_DIR[$name]}"
    local cmd="${SVC_CMD[$name]}"
    if [[ ! -d "$dir" ]]; then
      echo "[run] skip $name — dir missing: $dir"
      continue
    fi

    local bs="${SVC_BOOTSTRAP[$name]:-}"
    case "$bs" in
      python:*) ensure_python_venv "$dir" "${bs#python:}" ;;
      python)   ensure_python_venv "$dir" ;;
      node)     ensure_node_install "$dir" ;;
      "")       ;;
      *)        echo "[run] unknown bootstrap '$bs' for $name" ;;
    esac

    if [[ "${SVC_ENV_FROM_EXAMPLE[$name]:-}" == "1" \
          && "${BOOTSTRAP:-1}" == "1" \
          && ! -f "$dir/.env" \
          && -f "$dir/.env.example" ]]; then
      cp "$dir/.env.example" "$dir/.env"
    fi

    start_bg "$name" "$dir" "$cmd"

    local hurl="${SVC_HEALTH[$name]:-}"
    if [[ -n "$hurl" ]]; then
      wait_health "$name" "$hurl" "${SVC_HEALTH_TIMEOUT[$name]:-60}"
    fi
  done
}

# Tail every service log with a colored prefix; block until any service exits.
multiplex_logs() {
  echo
  echo "[run] all services launched. Tailing logs (Ctrl+C to stop all)."
  echo "[run] services: ${SVC_NAMES[*]}"
  echo

  for pfx in "${SVC_NAMES[@]}"; do
    local color
    color="$(color_for "$pfx")"
    ( tail -n 0 -F "$LOG_DIR/${pfx}.log" 2>/dev/null \
        | sed -u "s|^|${color}[${pfx}]${RST} |" ) &
    PIDS+=("$!")
  done

  wait -n
  echo "[run] a service exited — shutting the rest down"
  cleanup
}

parse_common_args() {
  BOOTSTRAP=1
  WITH_DB=0
  SKIP=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-bootstrap) BOOTSTRAP=0; shift ;;
      --with-db)      WITH_DB=1; shift ;;
      --skip) SKIP="$2"; shift 2 ;;
      -h|--help)
        cat <<EOF
Usage: $(basename "$0") [--no-bootstrap] [--with-db] [--skip name1,name2]
  --no-bootstrap   skip pip install / npm install
  --with-db        start docker-compose DBs before services that need them
  --skip <list>    omit specific services (comma-separated)
Services: ${SVC_NAMES[*]:-}
EOF
        exit 0
        ;;
      *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
  done
  if [[ -n "$SKIP" ]]; then
    local kept=()
    for n in "${SVC_NAMES[@]}"; do
      [[ ",$SKIP," == *",$n,"* ]] && continue
      kept+=("$n")
    done
    SVC_NAMES=("${kept[@]}")
  fi
}

has_service() {
  local target="$1"
  for n in "${SVC_NAMES[@]}"; do
    [[ "$n" == "$target" ]] && return 0
  done
  return 1
}

require_tcp() {
  local host="$1" port="$2" hint="${3:-}"
  if (echo > "/dev/tcp/$host/$port") 2>/dev/null; then
    return 0
  fi
  echo "[run] ERROR: TCP $host:$port unreachable" >&2
  [[ -n "$hint" ]] && echo "[run]   $hint" >&2
  return 1
}

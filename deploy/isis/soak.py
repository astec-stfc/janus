"""Weekend soak test: repeatedly randomise the beam's initial variables
(VM-GENERATOR PVs), trigger a simulation, and log settings + outcome.

Why the generator? epics-to-lattice reads generator values from EPICS into
the lattice on every trigger, so they genuinely propagate to the simulation.
(Section VM-*:INITIAL-CONDITIONS values do NOT propagate — their EPICS
read-back is disabled in set_lattice_from_epics.py — and unchanged settings
match a stored DB run, which replays results instead of simulating.)

Knobs are varied MULTIPLICATIVELY around the live baseline read at startup
(e.g. 0.5x-2.0x), so no unit assumptions are made. Edit KNOBS below.

The stack runs SIMULATION:MODE=TRIGGER, so each iteration puts
SIMULATION:START=ACTIVATE after setting the knobs; epics-to-lattice then
PATCHes the new lattice and the run proceeds. Outcome is read from
SIMULATION:STATUS (COMPLETE=0 / TRACKING=1 / ERROR=2).

Every iteration appends one JSON line to soak_logs/soak_<timestamp>.jsonl.
A human-readable log goes to stdout and soak_logs/soak_<timestamp>.log.

Remote use (through the pvagw gateway on the stack host):

    nohup python3 weekend_soak.py --epics-nameserver 130.246.90.69:5075 \
        --duration-hours 64 > /dev/null 2>&1 &
    tail -f soak_logs/soak_*.log

Inside the sandbox container no --epics-nameserver is needed.
Stop early with Ctrl-C / SIGTERM; a summary line is written on exit.
"""

import argparse
import json
import logging
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from p4p.client.thread import Context

# Multiplicative ranges applied to each knob's baseline value (read once at
# startup). Edit freely; knobs whose baseline reads as 0 are skipped.
KNOBS = {
    "VM-GENERATOR:CHARGE": (0.5, 2.0),
    "VM-GENERATOR:SIGMA_X": (0.5, 2.0),
    "VM-GENERATOR:SIGMA_Y": (0.5, 2.0),
}

# Beam-summary PVs sampled (best-effort) after each successful run.
RESULT_PVS = [
    "SIM-LATTICE:BEAM-SUMMARY:BETA_X",
    "SIM-LATTICE:BEAM-SUMMARY:BETA_Y",
    "SIM-LATTICE:BEAM-SUMMARY:SIGMA_X",
    "SIM-LATTICE:BEAM-SUMMARY:SIGMA_Y",
    "SIM-LATTICE:BEAM-SUMMARY:ENERGY",
]

STATUS_PV = "SIMULATION:STATUS"
UUID_PV = "SIMULATION:UUID"
START_PV = "SIMULATION:START"
GENERATOR_ENABLE_PV = "VM-GENERATOR:ENABLE"

# SimulationState / SimulationTrigger values (janus_common.schemas.elements)
COMPLETE, TRACKING, ERROR = 0, 1, 2
ACTIVATE = 1
STATE_NAMES = {COMPLETE: "COMPLETE", TRACKING: "TRACKING", ERROR: "ERROR"}

log = logging.getLogger("soak")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_int(value):
    """Decode an NTEnum/NTScalar monitor value to a plain int."""
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    for path in ("value.index", "value"):
        try:
            return int(value.raw[path])
        except Exception:
            continue
    raise ValueError(f"Cannot decode status value: {value!r}")


class StatusWatcher:
    """Monitor SIMULATION:STATUS; keep a timestamped trace of transitions."""

    def __init__(self, ctx: Context):
        self._trace = []  # [(time.time(), int_state), ...]
        self._lock = threading.Lock()
        self._sub = ctx.monitor(STATUS_PV, self._on_update, notify_disconnect=True)

    def _on_update(self, value):
        if isinstance(value, Exception):
            return  # disconnect notification; reconnect is automatic
        try:
            state = to_int(value)
        except ValueError:
            return
        with self._lock:
            self._trace.append((time.time(), state))

    def mark(self) -> int:
        with self._lock:
            return len(self._trace)

    def since(self, mark: int):
        with self._lock:
            return list(self._trace[mark:])

    def close(self):
        self._sub.close()


def wait_for(watcher, mark, predicate, timeout):
    """Wait until any status entry after `mark` satisfies predicate.

    Returns the matched state, or None on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        for _, state in watcher.since(mark):
            if predicate(state):
                return state
        time.sleep(0.2)
    return None


def read_results(ctx: Context) -> dict:
    """Best-effort read of beam-summary PVs; record final value + length."""
    out = {}
    for pv in RESULT_PVS:
        try:
            val = ctx.get(pv, timeout=10.0)
            arr = list(val)
            out[pv] = {"len": len(arr), "final": arr[-1] if arr else None}
        except Exception as err:
            out[pv] = {"error": f"{type(err).__name__}: {err}"}
    return out


def read_baselines(ctx: Context) -> dict:
    """Read the live baseline value of every knob; drop unusable ones."""
    baselines = {}
    for pv in KNOBS:
        try:
            value = float(ctx.get(pv, timeout=10.0))
        except Exception as err:
            log.warning("skipping knob %s: read failed (%s)", pv, err)
            continue
        if value == 0.0:
            log.warning("skipping knob %s: baseline is 0", pv)
            continue
        baselines[pv] = value
    return baselines


def run_iteration(ctx, watcher, rng, baselines, args):
    """One soak iteration. Returns the JSONL record for it."""
    record = {
        "type": "run",
        "time": utcnow(),
        "settings": {},
        "put_errors": {},
    }
    t0 = time.time()

    try:
        record["uuid_before"] = ctx.get(UUID_PV, timeout=10.0)
    except Exception as err:
        record["uuid_before"] = None
        record["uuid_before_error"] = str(err)

    # 1. randomise the generator knobs around their baselines
    for pv, baseline in baselines.items():
        lo, hi = KNOBS[pv]
        value = baseline * rng.uniform(lo, hi)
        record["settings"][pv] = value
        try:
            ctx.put(pv, value, timeout=5.0)
        except Exception as err:
            record["put_errors"][pv] = f"{type(err).__name__}: {err}"

    if len(record["put_errors"]) == len(baselines):
        record["outcome"] = "PUT_FAILED"
        record["duration_s"] = round(time.time() - t0, 3)
        return record

    # 2. trigger the run (deployment uses SIMULATION:MODE=TRIGGER)
    mark = watcher.mark()
    try:
        ctx.put(START_PV, ACTIVATE, timeout=5.0)
    except Exception as err:
        record["put_errors"][START_PV] = f"{type(err).__name__}: {err}"
        record["outcome"] = "PUT_FAILED"
        record["duration_s"] = round(time.time() - t0, 3)
        return record

    # 3. wait for tracking to start, then to finish
    started = wait_for(watcher, mark, lambda s: s == TRACKING, args.start_timeout)
    if started is None:
        record["outcome"] = "TIMEOUT_START"
    else:
        final = wait_for(
            watcher, mark, lambda s: s in (COMPLETE, ERROR), args.run_timeout
        )
        record["outcome"] = "TIMEOUT_RUN" if final is None else STATE_NAMES[final]

    record["status_trace"] = [
        (round(t - t0, 3), STATE_NAMES.get(s, s)) for t, s in watcher.since(mark)
    ]
    record["duration_s"] = round(time.time() - t0, 3)

    try:
        record["uuid_after"] = ctx.get(UUID_PV, timeout=10.0)
    except Exception as err:
        record["uuid_after"] = None
        record["uuid_after_error"] = str(err)

    if record["outcome"] == "COMPLETE":
        record["results"] = read_results(ctx)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--duration-hours", type=float, default=64.0,
                        help="stop after this many hours (default 64)")
    parser.add_argument("--iterations", type=int, default=0,
                        help="stop after N iterations (0 = unlimited)")
    parser.add_argument("--start-timeout", type=float, default=120.0,
                        help="seconds to wait for STATUS to reach TRACKING")
    parser.add_argument("--run-timeout", type=float, default=600.0,
                        help="seconds to wait for a run to finish once tracking")
    parser.add_argument("--settle", type=float, default=5.0,
                        help="pause between iterations, seconds")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for reproducible settings")
    parser.add_argument("--log-dir", default="soak_logs")
    parser.add_argument("--epics-nameserver", default=None, metavar="HOST:PORT",
                        help="EPICS_PVA_NAME_SERVERS for remote use, "
                             "e.g. 130.246.90.69:5075 (the pvagw gateway)")
    args = parser.parse_args()

    if args.epics_nameserver:
        os.environ["EPICS_PVA_NAME_SERVERS"] = args.epics_nameserver
        os.environ["EPICS_PVA_AUTO_ADDR_LIST"] = "NO"

    seed = args.seed if args.seed is not None else int(time.time())
    rng = random.Random(seed)

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = log_dir / f"soak_{stamp}.jsonl"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / f"soak_{stamp}.log"),
        ],
    )

    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())

    ctx = Context("pva")

    # generator must be enabled or its settings never reach the lattice
    try:
        ctx.put(GENERATOR_ENABLE_PV, True, timeout=10.0)
    except Exception as err:
        log.error("cannot enable generator (%s: %s) — aborting",
                  type(err).__name__, err)
        return 1

    baselines = read_baselines(ctx)
    if not baselines:
        log.error("no usable knobs (all baselines unreadable or 0) — aborting")
        return 1

    watcher = StatusWatcher(ctx)
    counts = {}
    deadline = time.time() + args.duration_hours * 3600

    with open(jsonl_path, "a", buffering=1) as jsonl:
        header = {
            "type": "header", "time": utcnow(), "seed": seed,
            "knobs": KNOBS, "baselines": baselines, "argv": sys.argv[1:],
        }
        jsonl.write(json.dumps(header) + "\n")
        log.info("soak started: seed=%s baselines=%s log=%s",
                 seed, baselines, jsonl_path)

        i = 0
        while not stop.is_set() and time.time() < deadline:
            if args.iterations and i >= args.iterations:
                break
            try:
                record = run_iteration(ctx, watcher, rng, baselines, args)
            except Exception as err:  # never let one iteration kill the soak
                record = {
                    "type": "run", "time": utcnow(),
                    "outcome": "EXCEPTION",
                    "error": f"{type(err).__name__}: {err}",
                }
            record["iteration"] = i
            jsonl.write(json.dumps(record, default=str) + "\n")

            counts[record["outcome"]] = counts.get(record["outcome"], 0) + 1
            log.info("iter %d %s in %.1fs (totals: %s)",
                     i, record["outcome"],
                     record.get("duration_s", 0), counts)

            # if EPICS looks dead, back off and rebuild the client context
            if record["outcome"] in ("PUT_FAILED", "EXCEPTION"):
                log.warning("EPICS trouble; reconnecting in 30s")
                stop.wait(30)
                try:
                    watcher.close()
                    ctx.close()
                except Exception:
                    pass
                ctx = Context("pva")
                watcher = StatusWatcher(ctx)

            i += 1
            stop.wait(args.settle)

        summary = {"type": "summary", "time": utcnow(),
                   "iterations": i, "outcomes": counts}
        jsonl.write(json.dumps(summary) + "\n")
        log.info("soak finished: %s", summary)

    watcher.close()
    ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

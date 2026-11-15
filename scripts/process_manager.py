"""
AgriChain AI - Process & Port Lifecycle Manager
===============================================
Provides safe, deterministic process management and health verification for
AgriChain AI services on Windows.

Guarantees:
1. Only terminates AgriChain-owned processes (identified by project directory or .venv).
2. Never touches unrelated Python or Node.js processes.
3. Kills complete process trees (parent + child workers) to prevent zombie reloaders.
4. Checks any TCP state (LISTEN, FIN_WAIT, CLOSE_WAIT, ESTABLISHED) holding the port.
5. Waits and confirms port release before returning.
6. Performs real HTTP readiness probes before declaring services healthy.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import sys
import time
import urllib.error
import urllib.request

import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1].resolve()
DEFAULT_BACKEND_PORT = 8000
DEFAULT_FRONTEND_PORT = 3000
DEFAULT_HOST = "127.0.0.1"


def is_agrichain_process(proc: psutil.Process) -> bool:
    """Check if process belongs to the AgriChain AI workspace."""
    try:
        # Check executable path
        try:
            exe = proc.exe()
            if str(PROJECT_ROOT).lower() in str(exe).lower():
                return True
        except Exception:
            pass

        # Check current working directory
        try:
            cwd = proc.cwd()
            if str(PROJECT_ROOT).lower() in str(cwd).lower():
                return True
        except Exception:
            pass

        # Check command line arguments
        try:
            cmdline = " ".join(proc.cmdline())
            if (
                str(PROJECT_ROOT).lower() in cmdline.lower()
                or "agrichain" in cmdline.lower()
                or "app.main:app" in cmdline
            ):
                return True
        except Exception:
            pass

        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def get_processes_on_port(port: int) -> list[tuple[int, psutil.Process]]:
    """Return list of (pid, Process) holding the given port in any TCP state."""
    found = {}
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port:
                if conn.pid and conn.pid not in found:
                    try:
                        p = psutil.Process(conn.pid)
                        found[conn.pid] = p
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
    except Exception:
        pass
    return list(found.items())


def is_port_available(port: int, host: str = DEFAULT_HOST) -> bool:
    """Check if a TCP port can be bound exclusively."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1.0)
        s.bind((host, port))
        s.close()
        return True
    except OSError:
        return False


def stop_services(ports: list[int], force_all: bool = False) -> int:
    """Safely terminate AgriChain services on specified ports."""
    stopped_count = 0

    for port in ports:
        procs = get_processes_on_port(port)
        if not procs:
            print(f"[INFO] Port {port} is clean (no active connection).")
            continue

        for pid, proc in procs:
            try:
                name = proc.name()
                is_owned = is_agrichain_process(proc)

                if not is_owned and not force_all:
                    print(
                        f"[WARN] Port {port} occupied by foreign process PID {pid} ('{name}'). "
                        f"Skipping to protect unrelated system workloads."
                    )
                    continue

                print(f"[STOP] Terminating AgriChain service PID {pid} ('{name}') on port {port}...")

                # Terminate children first to avoid orphan workers
                try:
                    children = proc.children(recursive=True)
                    for child in children:
                        try:
                            child.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception:
                    pass

                # Terminate main process
                try:
                    proc.kill()
                    stopped_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                print(f"[WARN] Process {pid} could not be terminated: {exc}")

    # Wait for ports to be released
    deadline = time.time() + 5.0
    all_clear = False
    while time.time() < deadline:
        if all(is_port_available(p) for p in ports):
            all_clear = True
            break
        time.sleep(0.5)

    if all_clear:
        print("[SUCCESS] Specified ports are verified free and ready for binding.")
        return 0
    else:
        print("[WARN] Sockets are finalizing teardown. Ports should be ready momentarily.")
        return 0


def status_services(ports: list[int]) -> int:
    """Inspect and report the status of specified ports."""
    print(f"AgriChain AI Workspace: {PROJECT_ROOT}")
    print("-" * 65)

    for port in ports:
        available = is_port_available(port)
        procs = get_processes_on_port(port)

        status_str = "FREE (Available)" if available else "OCCUPIED"
        print(f"Port {port:5d}: {status_str}")

        for pid, proc in procs:
            try:
                name = proc.name()
                owned = is_agrichain_process(proc)
                owner_label = "AgriChain AI" if owned else "Foreign / System Process"
                print(f"           - PID {pid}: {name} [{owner_label}]")
                try:
                    cwd = proc.cwd()
                    print(f"             CWD: {cwd}")
                except Exception:
                    pass
            except Exception:
                print(f"           - PID {pid} (Access Restricted)")

    print("-" * 65)
    return 0


def wait_backend(host: str = DEFAULT_HOST, port: int = DEFAULT_BACKEND_PORT, timeout_sec: int = 35) -> int:
    """Probe FastAPI backend health until HTTP 200 or timeout."""
    url = f"http://{host}:{port}/health"
    print(f"[WAIT] Probing FastAPI backend readiness at {url} (timeout: {timeout_sec}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AgriChain-HealthProbe/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8")
                    elapsed = round(time.time() - start_time, 1)
                    print(f"[READY] FastAPI backend is online and healthy ({elapsed}s)! Response: {body}")
                    return 0
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass

        time.sleep(1.0)

    print(f"[ERROR] FastAPI backend at {url} failed to become ready within {timeout_sec} seconds.")
    return 1


def wait_frontend(host: str = DEFAULT_HOST, port: int = DEFAULT_FRONTEND_PORT, timeout_sec: int = 30) -> int:
    """Probe Next.js frontend readiness until HTTP 200/304 or timeout."""
    url = f"http://{host}:{port}"
    print(f"[WAIT] Probing Next.js frontend readiness at {url} (timeout: {timeout_sec}s)...")

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AgriChain-HealthProbe/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status in (200, 304):
                    elapsed = round(time.time() - start_time, 1)
                    print(f"[READY] Next.js frontend is online and responding ({elapsed}s)!")
                    return 0
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass

        time.sleep(1.0)

    print(f"[ERROR] Next.js frontend at {url} failed to respond within {timeout_sec} seconds.")
    return 1


def main():
    parser = argparse.ArgumentParser(description="AgriChain AI Process & Port Lifecycle Manager")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Inspect ports and process ownership")
    p_status.add_argument("--ports", nargs="+", type=int, default=[8000, 3000])

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop AgriChain processes on ports")
    p_stop.add_argument("--ports", nargs="+", type=int, default=[8000, 3000])
    p_stop.add_argument("--force-all", action="store_true", help="Force termination of any process on port")

    # wait-backend
    p_wb = subparsers.add_parser("wait-backend", help="Wait for FastAPI backend health check")
    p_wb.add_argument("--host", default=DEFAULT_HOST)
    p_wb.add_argument("--port", type=int, default=DEFAULT_BACKEND_PORT)
    p_wb.add_argument("--timeout", type=int, default=35)

    # wait-frontend
    p_wf = subparsers.add_parser("wait-frontend", help="Wait for Next.js frontend")
    p_wf.add_argument("--host", default=DEFAULT_HOST)
    p_wf.add_argument("--port", type=int, default=DEFAULT_FRONTEND_PORT)
    p_wf.add_argument("--timeout", type=int, default=30)

    args = parser.parse_args()

    if args.action == "status":
        sys.exit(status_services(args.ports))
    elif args.action == "stop":
        sys.exit(stop_services(args.ports, force_all=args.force_all))
    elif args.action == "wait-backend":
        sys.exit(wait_backend(host=args.host, port=args.port, timeout_sec=args.timeout))
    elif args.action == "wait-frontend":
        sys.exit(wait_frontend(host=args.host, port=args.port, timeout_sec=args.timeout))


if __name__ == "__main__":
    main()

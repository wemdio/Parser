"""Restart an unresponsive API process without depending on its event loop."""

import http.client
import json
import os
import signal
import subprocess
import sys
import threading
import time


def api_responds():
    connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=5)
    try:
        connection.request("GET", "/health")
        response = connection.getresponse()
        if response.status != 200:
            return False
        payload = json.loads(response.read(16384))
        return isinstance(payload, dict) and payload.get("status") == "ok"
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def stop_child(child, diagnose=False):
    if child.poll() is not None:
        return
    if diagnose and hasattr(signal, "SIGUSR1"):
        try:
            child.send_signal(signal.SIGUSR1)
            time.sleep(1)
        except ProcessLookupError:
            return
    try:
        child.terminate()
        child.wait(timeout=20)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=10)


class Supervisor:
    def __init__(self, command, interval=20, startup_grace=180, failure_limit=3):
        self.command = command
        self.interval = interval
        self.startup_grace = startup_grace
        self.failure_limit = failure_limit
        self.stopping = threading.Event()

    def request_stop(self, *_):
        self.stopping.set()

    def run(self):
        child = None
        try:
            while not self.stopping.is_set():
                child = subprocess.Popen(self.command)
                print(f"[supervisor] Started API pid={child.pid}", flush=True)
                started = time.monotonic()
                ready = False
                failures = 0
                while not self.stopping.wait(self.interval):
                    if child.poll() is not None:
                        print(f"[supervisor] API exited code={child.returncode}", flush=True)
                        break
                    if api_responds():
                        ready = True
                        failures = 0
                        continue
                    if not ready and time.monotonic() - started < self.startup_grace:
                        continue
                    failures += 1
                    print(f"[supervisor] API health failed {failures}/{self.failure_limit}", flush=True)
                    if failures >= self.failure_limit:
                        print("[supervisor] Unresponsive API; dumping stacks and restarting", flush=True)
                        stop_child(child, diagnose=ready)
                        break
                if not self.stopping.is_set():
                    self.stopping.wait(10)
        finally:
            if child is not None:
                stop_child(child)


def supervise(script):
    supervisor = Supervisor([sys.executable, "-u", os.path.abspath(script), "--serve"])
    signal.signal(signal.SIGTERM, supervisor.request_stop)
    signal.signal(signal.SIGINT, supervisor.request_stop)
    supervisor.run()

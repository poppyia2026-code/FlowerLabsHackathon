#!/usr/bin/env python3
"""Exercise real local Flower processes with synthetic data (no cloud account).

Run: uv run python scripts/smoke_local_flower.py
Test decisions are automated; this is not a human-reviewed credential or
evidence of a SuperGrid deployment. Logs stay under ignored .flwr-local/.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from urllib.error import URLError
from urllib.request import urlopen
import zipfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from flwr.cli.build import build_fab_from_disk
from flwr.cli.chat.chat_app import parse_task_event, start_chat_run
from flwr.cli.typing import SuperLinkConnection
from flwr.cli.utils import init_http_client_from_connection
from flwr.proto.control_pb2 import ListNodesRequest, RegisterNodeRequest, StreamRunEventsRequest
from flwr.supercore.primitives.asymmetric import public_key_to_bytes

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("HospitalCred", "PayerEnrollment")


def make_certificates(folder: Path) -> None:
    now = datetime.now(timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP384R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Poppy local smoke CA")])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=1))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True,
                                       False, False), critical=True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
          .sign(ca_key, hashes.SHA384()))
    key = ec.generate_private_key(ec.SECP384R1())
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    cert = (x509.CertificateBuilder().subject_name(server_name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                           critical=False)
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"), x509.IPAddress(ip_address("127.0.0.1"))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(ca_key, hashes.SHA384()))
    (folder / "ca.crt").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    (folder / "server.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path = folder / "server.key"
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                         serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    key_path.chmod(0o600)


def free_ports() -> list[int]:
    sockets = [socket.socket() for _ in range(4)]
    try:
        for item in sockets:
            item.bind(("127.0.0.1", 0))
        return [item.getsockname()[1] for item in sockets]
    finally:
        for item in sockets:
            item.close()


def main() -> None:
    parent = ROOT / ".flwr-local"
    parent.mkdir(exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="smoke-", dir=parent))
    os.environ["FLWR_HOME"] = str(folder)
    env = {**os.environ, "ENDEAVOR_ENABLED": "0",
           "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")}
    processes = []
    logs = []
    client = None

    def launch(name: str, executable: str, args: list[str], node_home: Path):
        log = (folder / f"{name}.log").open("w")
        logs.append(log)
        proc = subprocess.Popen([str(Path(sys.executable).parent / executable), *args],
                                cwd=ROOT, env={**env, "FLWR_HOME": str(node_home)},
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(proc)
        return proc

    def turn(prompt: str, series=None):
        run, series = start_chat_run(client, prompt, None, series,
                                     fab_hash=hashlib.sha256(fab).hexdigest(), fab_content=fab)
        events = [dict(kind=kind, payload=payload)
                  for response in client.StreamRunEvents(StreamRunEventsRequest(run_id=run))
                  for kind, payload in [parse_task_event(response.task_event)]]
        (folder / f"run-{run}.json").write_text(json.dumps(events, indent=2))
        assert any(e["kind"] == "response.completed" for e in events), f"Run failed: {run}"
        print(f"Completed run {run}: {prompt}", flush=True)
        return run, series, events

    def receipt_events(events):
        return [e["payload"]["data"] for e in events if e["kind"] == "privcred.claim_receipt"]

    def stage(events, name):
        return next(e["payload"]["data"]["payload"] for e in events
                    if e["kind"] == "privcred.stage" and e["payload"]["data"]["stage"] == name)

    def deadline(_signum, _frame):
        raise TimeoutError(f"Smoke test exceeded 180 seconds; inspect {folder}")

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(180)
    started = time.monotonic()
    print(f"Real local Flower smoke; logs: {folder}", flush=True)
    try:
        make_certificates(folder)
        control, fleet, hospital, payer = free_ports()
        server = launch("superlink", "flower-superlink", [
            "--host", "127.0.0.1", "--port", str(control),
            "--fleet-api-address", f"127.0.0.1:{fleet}", "--enable-supernode-auth",
            "--ssl-certfile", str(folder / "server.crt"),
            "--ssl-keyfile", str(folder / "server.key"),
            "--ssl-ca-certfile", str(folder / "ca.crt"),
            "--disable-runtime-dependency-installation"], folder)
        tls = ssl.create_default_context(cafile=str(folder / "ca.crt"))
        for _ in range(100):
            assert server.poll() is None, "SuperLink exited; inspect logs"
            try:
                with urlopen(f"https://127.0.0.1:{control}/docs", context=tls, timeout=1):
                    break
            except (URLError, TimeoutError) as exc:
                startup_error = str(exc)
                time.sleep(0.2)
        else:
            raise TimeoutError(f"SuperLink did not start: {startup_error}")
        client = init_http_client_from_connection(SuperLinkConnection(
            name="poppy-smoke", address=f"127.0.0.1:{control}",
            root_certificates=str(folder / "ca.crt")))
        for role, port in zip(ROLES, (hospital, payer)):
            key = ec.generate_private_key(ec.SECP384R1())
            key_path = folder / f"{role}.key"
            key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                                  serialization.PrivateFormat.OpenSSH,
                                                  serialization.NoEncryption()))
            key_path.chmod(0o600)
            registered = client.RegisterNode(RegisterNodeRequest(
                public_key=public_key_to_bytes(key.public_key()), name=role))
            assert registered.node_id, f"Could not register {role}"
            data = ROOT / "fixtures" / "supernodes" / role / "providers.json"
            config = f"poppy-role={json.dumps(role)} poppy-data={json.dumps(str(data))}"
            launch(role, "flower-supernode", [
                "--superlink", f"127.0.0.1:{fleet}", "--root-certificates", str(folder / "ca.crt"),
                "--auth-supernode-private-key", str(key_path), "--node-config", config,
                "--host", "127.0.0.1", "--port", str(port)], folder / role)
        for _ in range(100):
            nodes = client.ListNodes(ListNodesRequest()).nodes_info
            if len(nodes) == 2 and all(n.status == "online" for n in nodes):
                break
            time.sleep(0.2)
        else:
            raise TimeoutError("Both SuperNodes did not come online")
        startup_seconds = round(time.monotonic() - started, 2)
        print(f"Both authenticated SuperNodes online in {startup_seconds}s", flush=True)
        fab = build_fab_from_disk(ROOT)
        with zipfile.ZipFile(io.BytesIO(fab)) as bundle:
            assert not any(n.startswith("fixtures/") for n in bundle.namelist())
        run, series, events = turn("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")
        assert not receipt_events(events), "Receipt issued before review"
        claims = stage(events, "claims_aggregated")
        assert claims["missing_nodes"] == []
        assert all(claims[k]["ok"] for k in ("hospital", "payer"))
        assert len(claims["hospital"]["claims"]) + len(claims["payer"]["claims"]) == 6
        _, _, wrong = turn("/approve wrong-review", series)
        assert not receipt_events(wrong)
        _, _, approved = turn(f"/approve run-{run} automated synthetic smoke test", series)
        receipts = receipt_events(approved)
        assert len(receipts) == 1 and receipts[0]["outcome"] == "credentialed"
        assert receipts[0]["run_id"] == f"run-{run}"
        _, _, replay = turn(f"/approve run-{run}", series)
        assert not receipt_events(replay), "Repeated decision issued another receipt"
        for action, outcome in (("escalate", "escalated"), ("reject", "rejected")):
            run, series, events = turn("Verify SYNTH-NPI-1888888888 for SYNTH-NETWORK-X")
            claims = stage(events, "claims_aggregated")
            assert claims["provider"]["provider_id"] == "SYNTH-NPI-1888888888"
            assert any(c["claim_type"] == "work_history_complete" and c["value"] is False
                       for c in claims["hospital"]["claims"])
            _, _, decided = turn(f"/{action} run-{run} automated synthetic smoke test", series)
            assert not receipt_events(decided)
            assert stage(decided, "complete")["outcome"] == outcome
        # Simulate an institution going offline in this isolated test only.
        payer_process = processes[-1]
        os.killpg(payer_process.pid, signal.SIGINT)
        payer_process.wait(timeout=10)
        run, series, events = turn("Verify SYNTH-NPI-1999999999 for SYNTH-NETWORK-X")
        assert "PayerEnrollment" in stage(events, "claims_aggregated")["missing_nodes"]
        _, _, decided = turn(f"/approve run-{run} automated missing-node test", series)
        assert stage(decided, "complete")["outcome"] == "failed"
        assert all(r["outcome"] != "credentialed" for r in receipt_events(decided))
        evidence = {"runtime": "local Flower 1.39, TLS, authenticated SuperNodes",
                    "synthetic": True, "automated_test_decisions": True,
                    "supergrid_verified": False, "startup_seconds": startup_seconds,
                    "checks": ["real node replies", "six claims", "no data in FAB", "pending review",
                               "persistent state", "wrong ID", "approve", "replay", "escalate", "reject",
                               "offline node cannot credential"]}
        (folder / "result.json").write_text(json.dumps(evidence, indent=2))
        print("PASS: " + ", ".join(evidence["checks"]), flush=True)
    finally:
        signal.alarm(0)
        if client:
            client.close()
        for proc in reversed(processes):
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGINT)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()

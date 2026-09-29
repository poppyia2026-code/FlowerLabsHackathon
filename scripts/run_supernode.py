#!/usr/bin/env python3
"""Start one real Flower SuperNode with an explicitly selected local data shard."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=['HospitalCred', 'PayerEnrollment'])
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--superlink', default='fleet-supergrid.flower.ai:443')
    parser.add_argument('--port', type=int, default=8011)
    args = parser.parse_args()
    data = args.data.resolve(strict=True)
    key = args.key.resolve(strict=True)
    catalog = json.loads(data.read_text())
    if catalog.get('meta', {}).get('synthetic') is not True:
        parser.error('Use synthetic data only for this demo')
    executable = shutil.which('flower-supernode')
    if not executable:
        parser.error('Install Flower 1.39 and activate its environment first')
    config = f'poppy-role={json.dumps(args.role)} poppy-data={json.dumps(str(data))}'
    command = [executable, '--superlink', args.superlink,
               '--auth-supernode-private-key', str(key), '--node-config', config,
               '--host', '127.0.0.1', '--port', str(args.port),
               '--allow-runtime-dependency-installation']
    os.execv(executable, command)


if __name__ == '__main__':
    main()

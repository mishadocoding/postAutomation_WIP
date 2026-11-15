"""Credential-free network diagnostic. Never generate, upload or publish."""
import getpass
import json
from pathlib import Path
import socket
import subprocess
import sys
from datetime import datetime, timezone
from urllib import error, request

import push_reel as p


def probe(host):
    result = {'host': host}
    try:
        socket.getaddrinfo(host, 443)
        result['dns'] = 'ok'
    except OSError as exc:
        result.update(dns='failed', reachable=False, failure=p.network_failure(exc))
        return result
    try:
        req = request.Request('https://' + host + '/', method='GET')
        with request.build_opener(p.NoRedirect()).open(req, timeout=10) as response:
            result.update(reachable=True, http_status=response.status)
    except error.HTTPError as exc:
        # Even a 400/401/403 response establishes that an HTTP server answered.
        # This does not establish account access or successful upload permission.
        result.update(reachable=True, http_status=exc.code)
        exc.close()
    except (error.URLError, OSError) as exc:
        result.update(reachable=False, failure=p.network_failure(exc))
    return result


def main():
    identity = getpass.getuser()
    if sys.platform == 'win32':
        process = subprocess.run(['whoami'], capture_output=True, text=True, timeout=10)
        if process.returncode == 0:
            identity = process.stdout.strip()
    report = {'time_utc': datetime.now(timezone.utc).isoformat(),
              'windows_user': identity, 'python': sys.executable,
              'proxy_configured': bool(request.getproxies()),
              'endpoints': [probe(host) for host in ('graph.facebook.com', 'rupload.facebook.com')],
              'note': 'HTTP reachability only. No credentials sent; no upload or publication attempted.'}
    destination = p.ROOT / '.state' / 'network' / 'latest.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('Saved report:', destination)
    return 0 if all(item['reachable'] for item in report['endpoints']) else 1


if __name__ == '__main__':
    sys.exit(main())

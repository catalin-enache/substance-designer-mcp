"""Send a Python file to the bridge plugin running inside Substance 3D Designer.

Usage:
    python sd_run.py script.py [--timeout SECONDS]
    python sd_run.py -c "print(1)" [--timeout SECONDS]
    python sd_run.py --status
    python sd_run.py --cancel
"""
import argparse
import hashlib
import hmac
import json
import os
import socket
import sys

PORT = int(os.environ.get('SD_BRIDGE_PORT', '9877'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from project_constants import PLUGIN, QUEUE_WAIT, TOKEN_FILE  # noqa: E402  (the plugin's name lives there)


def send(request, wait):
    """One request over the bridge protocol (see the plugin's docstring): the token never
    crosses the socket, only HMAC(token, nonce)."""
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    with socket.create_connection(('127.0.0.1', PORT), timeout=wait) as s:
        hello = b''
        while not hello.endswith(b'\n'):
            chunk = s.recv(1024)
            if not chunk:
                raise ConnectionError('the bridge closed the connection')
            hello += chunk
        nonce = json.loads(hello.decode('utf-8'))['nonce']
        request['auth'] = hmac.new(token.encode('utf-8'), nonce.encode('utf-8'), hashlib.sha256).hexdigest()
        s.sendall(json.dumps(request).encode('utf-8'))
        s.shutdown(socket.SHUT_WR)
        data = b''
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
    return json.loads(data.decode('utf-8'))


def _send_or_explain(request, wait):
    """send(), with a one-line explanation instead of a traceback when Designer can't be reached
    (REVIEW.md PLG-16)."""
    try:
        return send(request, wait)
    except ConnectionRefusedError:
        sys.stderr.write('Designer is not running, or its %s plugin is not loaded (port %d).\n'
                         % (PLUGIN, PORT))
        sys.exit(1)
    except FileNotFoundError:
        sys.stderr.write('No bridge token at %s: is the plugin installed (python3 install.py) and has '
                         'Designer started once since?\n' % TOKEN_FILE)
        sys.exit(1)
    except (socket.timeout, TimeoutError):
        sys.stderr.write('No reply from Designer after %ds; it may be busy, or a script may still be running '
                         '(sd_run.py --status, --cancel).\n' % wait)
        sys.exit(1)
    except ConnectionError as e:   # e.g. the bridge closed it: too many clients at once (REVIEW.md PLG-19)
        sys.stderr.write('Designer closed the connection (%s); try again in a moment.\n' % e)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('script', nargs='?')
    ap.add_argument('-c', dest='code')
    ap.add_argument('--timeout', type=float, default=0, help='abort the script after N seconds')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--cancel', action='store_true')
    args = ap.parse_args()

    if args.status or args.cancel:
        reply = _send_or_explain({'cmd': 'status' if args.status else 'cancel'}, 10)
    else:
        if args.code is not None:
            code, path = args.code, None
        elif args.script:
            path = os.path.abspath(args.script)
            with open(path, encoding='utf-8') as f:
                code = f.read()
        else:
            ap.error('give a script, -c CODE, --status or --cancel')
        request = {'code': code, 'path': path}
        if args.timeout:
            request['timeout'] = args.timeout
        # wait for the plugin's queue and the script itself, or a job we gave up on could start later
        wait = QUEUE_WAIT + (args.timeout or 900) + 60
        reply = _send_or_explain(request, wait)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors='replace')   # a cp1252 console can't print everything
    sys.stdout.write(reply['output'])
    if reply['output'] and not reply['output'].endswith('\n'):
        sys.stdout.write('\n')
    if not reply['ok']:
        sys.stderr.write(reply['error'])
        sys.exit(1)


if __name__ == '__main__':
    main()

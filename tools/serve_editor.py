#!/usr/bin/env python3
"""Launch the browser-local editor, bound to loopback only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import webbrowser

parser=argparse.ArgumentParser()
parser.add_argument('--no-open',action='store_true')
parser.add_argument('--port',type=int,default=0)
args=parser.parse_args()
directory=Path(__file__).resolve().parents[1]/'PicoStation Menu Editor'
class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript'}
server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(directory)))
url=f'http://127.0.0.1:{server.server_port}'
print(f'PicoStation Menu Editor : {url}\nFerme cette fenêtre ou utilise Ctrl+C pour arrêter.',flush=True)
if not args.no_open:webbrowser.open(url)
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()

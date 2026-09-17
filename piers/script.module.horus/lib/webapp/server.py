# -*- coding: utf-8 -*-
# EKHorus - The web server: static files and the json api.
#
# It answers on the whole local network with no password, which is what the rest of the
# EspaKodi addons do too and what makes it usable: typing an address is the point. The one
# door that is bolted is the browser one, see _host_valido().

import os
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lib.utils import logger, runtime_path

from . import api

ESTATICOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
MEDIOS = os.path.join(runtime_path, 'resources', 'media')

# The only bodies this serves are a handful of fields. Anything larger is refused without
# reading it, and its connection closed.
CUERPO_MAXIMO = 65536

_TIPOS = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.json': 'application/json; charset=utf-8',
}


def _anfitrion(cabecera):
    """Address part of the Host header, with no port."""
    return (cabecera or '').split(':')[0].strip('[]')


def _host_valido(cabecera):
    """True if the request arrives addressed to a bare address and not to a name.

    This is the only real defence the server needs. A page the user is browsing cannot
    read our answers (the api sends no permissive CORS), but it CAN fire requests at
    192.168.x.x blindly, and with a name that resolves to the local network it could even
    read them back. Demanding the Host be an ip closes that second door, and no legitimate
    use loses anything: nobody reaches this by a domain name."""
    host = _anfitrion(cabecera)

    if host in ('localhost', '::1'):
        return True

    partes = host.split('.')

    return len(partes) == 4 and all(p.isdigit() and len(p) <= 3 for p in partes)


class Manejador(BaseHTTPRequestHandler):

    # The default one answers 1.0, and with it every response needs to close the
    # connection. The page asks for a handful of things at once when it opens.
    protocol_version = 'HTTP/1.1'

    def log_message(self, formato, *args):
        # The base class writes to stderr, and in Kodi that is the log: a page with
        # thirty logos would put thirty lines in it per opening.
        pass

    def do_GET(self):
        self._atender('GET')

    def do_POST(self):
        self._atender('POST')

    # --- plumbing -------------------------------------------------------------------

    def _responder(self, codigo, tipo, cuerpo, cache=None):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode('utf-8')

        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(cuerpo)))
        if cache:
            self.send_header('Cache-Control', cache)
        self.end_headers()

        try:
            self.wfile.write(cuerpo)
        except OSError:
            # The phone locking its screen mid-answer is not a fault worth logging.
            pass

    def _cuerpo_peticion(self):
        """The body of the request, read WHOLE whatever we then do with it.

        Leaving it in the socket is what desynchronises a kept-alive connection: the next
        request would start reading in the middle of this body. Hence it is read here, at
        the top, and not inside the branch that happens to want it."""
        try:
            largo = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return b''

        if largo <= 0:
            return b''

        # A body is only ever a handful of fields. Something bigger is not ours, and
        # draining it to keep the connection tidy would be doing the sender a favour.
        if largo > CUERPO_MAXIMO:
            self.close_connection = True
            return b''

        return self.rfile.read(largo)

    def _atender(self, metodo):
        cuerpo_peticion = self._cuerpo_peticion() if metodo == 'POST' else b''

        if not _host_valido(self.headers.get('Host')):
            self._responder(403, 'text/plain; charset=utf-8', 'Host no permitido')
            return

        ruta, _, consulta = self.path.partition('?')
        parametros = dict(urllib.parse.parse_qsl(consulta))

        if ruta == '/api/apagar':
            # It cannot be answered from api.py: shutting down needs the server object,
            # and shutdown() waits for serve_forever, which is what is running this very
            # request. Hence the answer first and the thread afterwards.
            self._responder(200, 'application/json; charset=utf-8', '{"ok":true}')
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        if ruta.startswith('/api/'):
            try:
                codigo, tipo, cuerpo = api.atender(metodo, ruta, parametros,
                                                   cuerpo_peticion,
                                                   _anfitrion(self.headers.get('Host')))
            except Exception as e:
                logger(f'webapp: {ruta}: {e}', 'error')
                codigo, tipo, cuerpo = 500, 'application/json; charset=utf-8', '{"error":1}'

            self._responder(codigo, tipo, cuerpo, cache='no-store')
            return

        if ruta.startswith('/media/'):
            # The flags and the category icons the addon already ships. Serving them saves
            # drawing them again for the web and keeps both interfaces looking alike.
            self._fichero(MEDIOS, ruta[len('/media/'):], cache='public, max-age=86400')
            return

        # Whatever is not a file is the page itself: the interface navigates on its own
        # and reloading it on any address has to come back with the app, not with a 404.
        self._fichero(ESTATICOS, ruta.lstrip('/') or 'index.html',
                      respaldo='index.html', cache='no-cache')

    def _fichero(self, raiz, relativa, respaldo=None, cache=None):
        completa = os.path.join(raiz, relativa.replace('/', os.sep))

        if not os.path.realpath(completa).startswith(os.path.realpath(raiz) + os.sep) \
                or not os.path.isfile(completa):
            if not respaldo:
                self._responder(404, 'text/plain; charset=utf-8', 'No esta')
                return
            completa = os.path.join(raiz, respaldo)

        try:
            with open(completa, 'rb') as f:
                datos = f.read()
        except OSError as e:
            logger(f'webapp: no se pudo leer {completa}: {e}', 'error')
            self._responder(404, 'text/plain; charset=utf-8', 'No esta')
            return

        extension = os.path.splitext(completa)[1].lower()
        self._responder(200, _TIPOS.get(extension, 'application/octet-stream'), datos,
                        cache=cache)


class Servidor(ThreadingHTTPServer):
    # Without this a phone that walks off with a connection open keeps Kodi from
    # closing the server.
    daemon_threads = True

    # On Windows SO_REUSEADDR lets a second socket bind a port somebody is already
    # listening on, and which of the two gets the connections is anyone's guess. Everywhere
    # else it only forgives TIME_WAIT, which is what lets the server come back after a
    # hard stop, so it is worth keeping there.
    allow_reuse_address = os.name != 'nt'


def crear_servidor(host, puerto):
    return Servidor((host, puerto), Manejador)

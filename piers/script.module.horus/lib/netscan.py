# -*- coding: utf-8 -*-
# EKHorus. Licensed GPL-3.0-or-later, see LICENSE.
"""Find AceStream engines on the local network.

The scenario in the guide where the engine lives on another device requires the user to
know its IP address. This looks it up for them: it opens the port on the 254 addresses of
the subnet and asks the version of whichever ones answer.

The cheap filter is a TCP connection with a short timeout. Asking over HTTP on 254
addresses would take minutes; opening a socket to each one and keeping only those that
respond costs a couple of seconds.
"""
import socket
import threading

import xbmc

from lib.utils import (ENGINE_ACESERVE, ENGINE_ACESTREAM, HOSTS_LOCALES, engine_name,
                       logger)
from acestream.server import Server

PUERTO_POR_OMISION = 6878
# 32 at a time over 254 addresses is eight rounds. More threads do not speed it up: what
# rules is the timeout, and a TV box with 254 sockets open at once does no better.
OBREROS = 32
# A device on the local network answers in milliseconds. This margin is for lossy wifi.
TIMEOUT_PUERTO = 0.4
TIMEOUT_VERSION = 3
TIMEOUT_MOTOR = 2

PESTILLO = 'ekhorus.barrido'

_PRIVADAS = ('10.', '192.168.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.',
             '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.',
             '172.28.', '172.29.', '172.30.', '172.31.')


def ip_local():
    """IP of this device on its network, or an empty string."""
    direccion = ''

    try:
        direccion = (xbmc.getIPAddress() or '').strip()
    except (AttributeError, TypeError):
        pass

    if direccion and direccion not in HOSTS_LOCALES:
        return direccion

    # Kodi may not know it. The UDP socket trick does not send a single packet: connect()
    # over UDP only fixes the destination, and with that the system already picks which
    # interface it would go out through and reveals the source address.
    sonda = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sonda.connect(('10.255.255.255', 1))
        return sonda.getsockname()[0]
    except OSError as e:
        logger(f'netscan: no se pudo averiguar la ip local: {e}', 'error')
        return ''
    finally:
        sonda.close()


def es_privada(direccion):
    return bool(direccion) and direccion.startswith(_PRIVADAS)


def subred(direccion):
    """['192.168.1.1', ...] of the /24 it belongs to, without its own, the .0 or the .255."""
    partes = direccion.split('.')
    if len(partes) != 4:
        return list()

    prefijo = '.'.join(partes[:3])

    return [f'{prefijo}.{n}' for n in range(1, 255) if f'{prefijo}.{n}' != direccion]


def _puerto_abierto(direccion, puerto):
    try:
        with socket.create_connection((direccion, puerto), timeout=TIMEOUT_PUERTO):
            return True
    except OSError:
        return False


def barrer(puerto=PUERTO_POR_OMISION, al_avanzar=None, cancelar=None):
    """[(ip, version, engine)] of the engines found, sorted by address.

    'al_avanzar(hechas, total)' is called by the thread that calls this, not by the
    workers, because the one holding the progress dialog is the main thread. 'cancelar'
    is a threading.Event: once set, the workers finish the address they have in hand and
    leave."""
    propia = ip_local()

    if not es_privada(propia):
        logger(f'netscan: {propia or "sin ip"} no es una red domestica, no se barre')
        return None

    direcciones = subred(propia)
    total = len(direcciones)
    abiertas = list()
    siguiente = [0]
    candado = threading.Lock()

    def obrero():
        while True:
            if cancelar is not None and cancelar.is_set():
                return

            with candado:
                if siguiente[0] >= total:
                    return
                indice = siguiente[0]
                siguiente[0] += 1

            if _puerto_abierto(direcciones[indice], puerto):
                with candado:
                    abiertas.append(direcciones[indice])

    hilos = [threading.Thread(target=obrero, daemon=True) for _ in range(OBREROS)]
    for hilo in hilos:
        hilo.start()

    monitor = xbmc.Monitor()
    ultimo = -1

    while any(h.is_alive() for h in hilos):
        with candado:
            hechas = min(siguiente[0], total)

        # Only when the number changes. Reporting on every turn would tie the dialog's
        # repaint rate to this loop's, and it only takes waitForAbort returning early to
        # end up repainting thousands of times a second.
        if al_avanzar is not None and hechas != ultimo:
            ultimo = hechas
            al_avanzar(hechas, total)

        # If Kodi is shutting down there is no point in carrying on sweeping the network.
        if monitor.waitForAbort(0.2):
            if cancelar is not None:
                cancelar.set()
            break

    # No join: the workers are daemons and their timeout is tenths of a second, so they
    # die on their own. Waiting for them here would leave Kodi hung when closing the
    # script.
    if cancelar is not None and cancelar.is_set():
        return list()

    encontrados = list()
    for direccion in sorted(abiertas, key=lambda d: [int(x) for x in d.split('.')]):
        servidor = Server(host=direccion, port=puerto, timeout=TIMEOUT_VERSION)
        version = servidor.version

        if not version:
            # The port was open but there is no engine on the other side: a router, a
            # printer, anything. It is not an error, it simply is not of interest.
            logger(f'netscan: {direccion}:{puerto} abierto pero no es un motor')
            continue

        # With no clear answer to /pl.m3u the engine is not named: better to show the
        # address and the version than to hang a label on it that may be false.
        sirve = servidor.playlist_status(timeout=TIMEOUT_MOTOR)
        motor = '' if sirve is None else engine_name(ENGINE_ACESERVE if sirve
                                                     else ENGINE_ACESTREAM)
        encontrados.append((direccion, version, motor))

    return encontrados

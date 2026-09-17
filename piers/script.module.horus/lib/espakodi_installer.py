# -*- coding: utf-8 -*-
# EKHorus - Copyright (C) 2024-2026 RubenSDFA1laberot (github.com/fullstackcurso)
# License: GPL-2.0-or-later - See the LICENSE file for more details.
# Installation module for the EspaKodi ecosystem.
#
# Ported from the espakodi_installer.py in plugin.program.espakodi.installer, with the
# same three addon families (repo / official / embedded) and these differences:
#  - No requests and no six. EKHorus does not declare them in addon.xml, so the helpers
#    http_get_bytes/http_get_text from lib.utils are used, which already bring a time
#    limit, a User-Agent and a size cap
#  - The listitem urls are built with Item().tourl(), because EKHorus routes Items in
#    base64 and plain query strings only work for action=play
#  - The menu also includes the APK download, which belongs to EKHorus
#  - render_menu() does not close the directory: that is done by cerrar_directorio() in
#    default.py, which keeps count so as not to close it twice
#  - Out goes the green "new" dot (espakodi_addons_seen). In the addons it comes from
#    that setting is not even declared in settings.xml, so setSetting() does nothing
#    and the dot never goes away

import json
import os
import re
import shutil
import sys
import zipfile

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from lib import list_screen, ui_common
from lib.utils import Item, HEADING, logger, http_get_bytes, http_get_text

EK_REPO_POLL_TIMEOUT_S  = 20
EK_ADDON_POLL_TIMEOUT_S = 60
EK_PROXY_POLL_TIMEOUT_S = 25  # repository.elementumorg raises its local proxy asynchronously
EK_POLL_INTERVAL_MS     = 500
EK_MAX_REPO_ZIP_BYTES   = 50 * 1024 * 1024
EK_MAX_ADDON_ZIP_BYTES  = 200 * 1024 * 1024
EK_HTTP_TIMEOUT_S       = 30

EK_ELEMENTUM_REPO = "repository.elementumorg"

# EKHorus does not appear in EK_ADDONS (installing itself makes no sense), so this never
# matches anything. It is kept for parity with the addons it comes from
EK_OWN_ADDON_ID = "script.module.horus"

# How each addon is installed:
#   "repo":     the repo zip is fetched, registered and the addon installed (general case)
#   "official": it lives in the official Kodi repo, always there -> direct InstallAddon
#   "embedded": the repo travels inside EKHorus (resources/repos) -> copied and installed
#
# (addon_id, repo_id, zip_url, source_url, name, plot, fallback_icon, mode, kind)
# kind = section of the repo where Kodi files it, only for the manual instructions
EK_ADDONS = [
    (
        "plugin.video.espatv",
        "repository.espatv",
        "https://raw.githubusercontent.com/espakodi/espatv/main/repository.espatv-1.0.0.zip",
        "https://espakodi.github.io/espatv/",
        "EspaTV",
        "TDT, RTVE a la carta, búsqueda en YouTube y Dailymotion, catálogo de vídeos, radio, podcasts, reproducción de enlaces, noticias, meteorología, agenda deportiva y mucho más.",
        "directo.png",
        "repo",
        "vídeo",
    ),
    (
        "plugin.video.espadaily",
        "repository.espadaily",
        "https://fullstackcurso.github.io/espadaily/repository.espadaily-1.0.2.zip",
        "https://fullstackcurso.github.io/espadaily/",
        "EspaDaily",
        "EspaDaily permite explorar catálogos de televisión española y buscar vídeos públicos en internet que coincidan.",
        "busqueda.png",
        "repo",
        "vídeo",
    ),
    (
        "plugin.video.atresdaily",
        "repository.atresdaily",
        "https://espatv.github.io/atresdaily/repository.atresdaily-1.0.1.zip",
        "https://espatv.github.io/atresdaily/",
        "AtresDaily",
        "Disfruta del contenido de A3Player con la potencia de AtresDaily. Búsquedas inteligentes y programación en directo.",
        "play_generic.png",
        "repo",
        "vídeo",
    ),
    (
        "plugin.program.loiolog",
        "repository.loiolog",
        "https://raw.githubusercontent.com/loioloio/loiolog/main/repository.loiolog-1.0.0.zip",
        "https://loioloio.github.io/loiolog/",
        "loiolog",
        "Visualiza y busca en el log de Kodi con un visor de colores por severidad. Filtra por addon, texto o expresiones regulares. Exporta a TXT o JSON, comparte el log subiéndolo a internet o ábrelo en el móvil desde tu red local. Consulta estadísticas del log, compara errores entre sesiones y gestiona los logs anteriores.",
        "adv_log.png",
        "repo",
        "programa",
    ),
    (
        "plugin.program.flowfavmanager",
        "repository.flowfavmanager",
        "https://loioloio.github.io/flowfav/repository.flowfavmanager-1.0.0.zip",
        "https://loioloio.github.io/flowfav/",
        "Flow FavManager",
        "Flow FavManager mejora la experiencia de gestión de favoritos en Kodi.\nPermite organizarlos, personalizar su apariencia y las acciones que realizan. Incluye herramientas de copia de seguridad, un editor intuitivo, perfiles y ordenación por secciones, entre otras funciones.",
        "favoritos.png",
        "repo",
        "programa",
    ),
    (
        "plugin.video.streamninja",
        "repository.streamninja",
        "https://raw.githubusercontent.com/fullstackcurso/estreamninja/main/repository.streamninja-1.0.0.zip",
        "https://fullstackcurso.github.io/estreamninja/",
        "StreamNinja",
        "StreamNinja permite enviar URLs a Kodi desde un móvil o PC mediante una web local efímera, o bien recibirlas directamente desde otros addons. Soporta Dailymotion, YouTube, AceStream, Torrents y casi cualquier enlace de vídeo.",
        "srch_externa.png",
        "repo",
        "vídeo",
    ),
    (
        "plugin.video.topzilla",
        "repository.topzilla",
        "https://raw.githubusercontent.com/espatv/topzilla/main/repository.topzilla-1.0.0.zip",
        "https://espatv.github.io/topzilla/",
        "TopZilla",
        "TopZilla muestra rankings, información y vídeos relacionados de películas y series. Además permite buscarlas, filtrarlas y guardarlas en tu biblioteca o consultar sus fichas con solo dos clics, estés donde estés en tu Kodi.",
        "busqueda.png",
        "repo",
        "vídeo",
    ),
    (
        "plugin.program.loiolink",
        "repository.loiolink",
        "https://loiolo.io/repository.loiolink-1.0.0.zip",
        "https://loiolo.io/",
        "loiolink",
        "• Mando a distancia: controla lo que estás viendo, navega por los menús o gestiona tus addons desde la web.\n• Toda tu colección: navega por tus películas, series y música desde el navegador y reprodúcelas en la TV.\n• Streaming al móvil: envía el vídeo desde el televisor a tu móvil, tablet o PC.\n• Favoritos: elimina, reordena o edita accesos directos desde el navegador.\n• Escribe sin el mando: escribe búsquedas o enlaces largos en el navegador y aparecerán al instante en Kodi.\n• Envío de vídeos, torrents, listas M3U o enlaces AceStream para reproducirlos al vuelo o grabarlos.\n• Escáner web y Telegram: rastrea páginas o canales para recopilar y reproducir torrents, vídeos y enlaces.\n• Instalación de addons y archivos: envía ZIPs de addons o APKs desde el navegador para instalarlos al instante.\n• Grabación HLS, explorador de archivos, apagado remoto y copia de seguridad.",
        "info.png",
        "repo",
        "programa",
    ),
    (
        "plugin.video.elementum",
        EK_ELEMENTUM_REPO,
        "",
        "https://github.com/elgatito/plugin.video.elementum",
        "Elementum",
        "Elementum es un motor de búsqueda y reproducción de torrents para Kodi. Reproduce películas y series por streaming desde la red BitTorrent mediante providers que se instalan aparte.\n\nSu repositorio viaja dentro de EKHorus, así que no hace falta añadir ninguna fuente.",
        "srch_torrent.png",
        "embedded",
        "vídeo",
    ),
    (
        "script.module.youtube.dl",
        "repository.xbmc.org",
        "",
        "https://github.com/xbmc/repo-scripts",
        "youtube-dl",
        "Módulo youtube-dl/yt-dlp para Kodi: resuelve la URL reproducible de cientos de webs de vídeo. Lo usan otros addons como motor de extracción, no tiene interfaz propia.\n\nSe instala desde el repositorio oficial de Kodi.",
        "adv_ytdlp.png",
        "official",
        "programa",
    ),
    (
        "plugin.program.ekgames",
        "repository.ekgames",
        "https://espatv.github.io/ekgames/repository.ekgames-1.0.0.zip",
        "https://espatv.github.io/ekgames/",
        "EKGames",
        "Catorce minijuegos clásicos para echar una partida sin salir de Kodi: Snake, 2048, Tetris, Buscaminas, Memoria, Solitario, Flappy, Pong, Invaders, Burbujas, Frogger, Galaga, Asteroids y Pac-Man.\nSe juegan con el mando a distancia, con un mando de juego, con el teclado o con los dedos, guardan su récord y tienen cuatro niveles de dificultad.\nIncluye además Gamesek entero, sin instalar nada más: emuladores por sistema, tus carpetas de juegos, juegos libres que se descargan solos y el Modo Juego a pantalla completa.",
        "juegos.png",
        "repo",
        "programa",
    ),
    (
        "plugin.program.gamesek",
        "repository.gamesek",
        "https://espakodi.github.io/gamesek/repository.gamesek-1.0.0.zip",
        "https://espakodi.github.io/gamesek/",
        "Gamesek",
        "Juegos y emuladores para Kodi, en español. Trae catorce clásicos que se abren al momento, sin descargar nada y sin emulador, y otros tantos que se descargan e instalan solos.\nTambién puedes importar tus juegos, enviarlos desde el móvil por la red de casa o pedirle que los busque por tus discos. El Modo Juego lo enseña todo a pantalla completa.",
        "juegos.png",
        "repo",
        "programa",
    ),
    (
        "inputstream.adaptive",
        "repository.xbmc.org",
        "",
        "https://github.com/xbmc/inputstream.adaptive",
        "InputStream Adaptive",
        "Motor de reproducción para streaming adaptativo (DASH, HLS, Smooth Streaming). Lo usan muchos addons de vídeo (TV a la carta, directos) para reproducir. Normalmente se instala solo al instalar un addon que lo necesite; esta opción lo instala a mano desde el repositorio oficial de Kodi.",
        "directo.png",
        "official",
        "InputStream",
    ),
    (
        "script.module.resolveurl",
        "repository.resolveurl",
        "",
        "https://github.com/Gujal00/ResolveURL",
        "ResolveURL",
        "Módulo que resuelve el enlace reproducible de cientos de servidores de vídeo. Lo usan muchos addons para reproducir enlaces de hosters. Normalmente se instala solo al instalar un addon que lo declare; esta opción lo instala a mano desde su repositorio (incluido en EspaKodi).",
        "play_generic.png",
        "official",
        "programa",
    ),
]

_EK_BY_ID = {row[0]: row for row in EK_ADDONS}

# The screen order lives apart from the catalogue so things can be moved around without
# touching the tuples. Espanime, in an "Otros addons" block in the installer, is not here.
EK_BLOQUES = [
    ("Addons de EspaKodi", [
        "plugin.video.espatv",
        "plugin.video.espadaily",
        "plugin.video.atresdaily",
        "plugin.program.loiolink",
        "plugin.program.flowfavmanager",
        "plugin.video.streamninja",
        "plugin.video.topzilla",
        "plugin.program.loiolog",
        "plugin.program.ekgames",
        "plugin.program.gamesek",
    ]),
    ("Dependencias y motores", [
        "script.module.youtube.dl",
        "plugin.video.elementum",
        "inputstream.adaptive",
        "script.module.resolveurl",
    ]),
]


def _ek_bloques():
    """(title, entries) of each block. Whatever is in the catalogue and in no block falls
    into a final one, so adding an addon and forgetting the list does not hide it."""
    colocados = set()
    bloques = list()

    for titulo, ids in EK_BLOQUES:
        entradas = [_EK_BY_ID[i] for i in ids if i in _EK_BY_ID]
        colocados.update(row[0] for row in entradas)
        if entradas:
            bloques.append((titulo, entradas))

    sueltos = [row for row in EK_ADDONS if row[0] not in colocados]
    if sueltos:
        bloques.append(("Otros", sueltos))

    return bloques


def _ek_download_bytes(url, max_bytes, timeout=EK_HTTP_TIMEOUT_S):
    # http_get_bytes already sets a User-Agent, a time limit and a size cap (and blows up
    # if it is exceeded). All that is left here is checking that what arrived is a real ZIP
    content = http_get_bytes(url, timeout=timeout, max_bytes=max_bytes)

    if len(content) < 4 or content[:2] != b"PK":
        raise Exception("El archivo descargado no es un ZIP valido")

    return content


def _ek_download_text(url, timeout=20):
    return http_get_text(url, timeout=timeout)


def _ek_extract_zip(zip_path, addons_dir):
    # A zip with paths like ../../ would step outside addons/ and write wherever it wanted.
    # The prefix is compared with the trailing separator (addons_dir + os.sep): without it,
    # a sibling path like ../addons_evil/x would pass the filter by starting like addons
    addons_dir_real = os.path.realpath(addons_dir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for entry in zf.namelist():
            resolved = os.path.realpath(os.path.join(addons_dir, entry))
            if resolved != addons_dir_real and not resolved.startswith(addons_dir_real + os.sep):
                raise Exception("ZIP contiene ruta sospechosa: {0}".format(entry))
        zf.extractall(addons_dir)


def _ek_copytree(src, dst):
    # shutil.copytree(dirs_exist_ok=) is Python 3.8. Copying by hand works on any version
    # and on top of that does not blow up if the target folder already exists
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        if not os.path.isdir(target):
            os.makedirs(target)
        for name in files:
            shutil.copy2(os.path.join(root, name), os.path.join(target, name))


def _ek_addon_is_installed(addon_id):
    # System.HasAddon = installed and enabled. It is used instead of xbmcaddon.Addon()
    # because that one logs an "EXCEPTION: Unknown addon id" in kodi.log for every addon
    # that is not installed (we would catch it in Python, but the log gets dirty), and is slower
    return xbmc.getCondVisibility("System.HasAddon({0})".format(addon_id))


def _ek_addon_dir_present(addon_id):
    addon_dir = xbmcvfs.translatePath("special://home/addons/{0}/".format(addon_id))
    return os.path.isdir(addon_dir) and os.path.isfile(os.path.join(addon_dir, "addon.xml"))


def _ek_jsonrpc(method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        req["params"] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except Exception:
        return {}


def _ek_addon_is_known(addon_id):
    resp = _ek_jsonrpc("Addons.GetAddonDetails", {"addonid": addon_id, "properties": ["enabled"]})
    return "result" in resp and "addon" in resp.get("result", {})


def _ek_enabled_ids():
    # Set of installed and enabled addonids, in a single call. It paints the whole menu
    # without asking addon by addon
    resp = _ek_jsonrpc("Addons.GetAddons", {"enabled": True})
    addons = resp.get("result", {}).get("addons", []) if "result" in resp else []
    return {a.get("addonid") for a in addons}


def _ek_addon_available_in_repos(addon_id):
    # Addons that the repositories offer and are not installed yet. It tells whether the
    # repo index is ready already: in elementum, showing up here means that its local
    # proxy is answering
    resp = _ek_jsonrpc("Addons.GetAddons", {"installed": False, "properties": ["name"]})
    addons = resp.get("result", {}).get("addons", []) if "result" in resp else []
    return any(a.get("addonid") == addon_id for a in addons)


def _ek_enable_addon_jsonrpc(addon_id):
    resp = _ek_jsonrpc("Addons.SetAddonEnabled", {"addonid": addon_id, "enabled": True})
    return resp.get("result") == "OK"


def _ek_try_recover_addon(addon_id):
    # If the addon is there but disabled there is nothing to download, re-enabling is enough
    if _ek_addon_is_known(addon_id):
        if _ek_enable_addon_jsonrpc(addon_id):
            xbmc.sleep(800)
            if _ek_addon_is_installed(addon_id):
                return True
    if not _ek_addon_dir_present(addon_id):
        return False
    xbmc.executebuiltin("UpdateLocalAddons()")
    xbmc.sleep(1500)
    if _ek_addon_is_known(addon_id) and _ek_enable_addon_jsonrpc(addon_id):
        xbmc.sleep(800)
        if _ek_addon_is_installed(addon_id):
            return True
    xbmc.executebuiltin("EnableAddon({0})".format(addon_id))
    xbmc.sleep(1500)
    return _ek_addon_is_installed(addon_id)


def _ek_addon_icon(addon_id, fallback=None, installed=None):
    # Addon() is only instantiated if it is installed, to keep the rest out of the log
    if installed is None:
        installed = _ek_addon_is_installed(addon_id)
    if installed:
        try:
            path = xbmcaddon.Addon(addon_id).getAddonInfo("path")
            for name in ("icon.png", "icon.jpg"):
                p = os.path.join(path, name)
                if os.path.exists(p):
                    return p
        except Exception:
            pass
    return fallback or os.path.join(_media_dir(), "play_generic.png")


def _media_dir():
    return os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "media")


def _addon_fanart():
    return xbmcaddon.Addon().getAddonInfo("fanart")


def _ek_get_repo_datadir(repo_id):
    repo_xml = xbmcvfs.translatePath("special://home/addons/{0}/addon.xml".format(repo_id))
    if not os.path.isfile(repo_xml):
        return None
    try:
        with open(repo_xml, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r"<datadir[^>]*>\s*([^<\s]+)\s*</datadir>", content)
        if m:
            url = m.group(1).strip()
            if not url.endswith("/"):
                url += "/"
            return url
    except Exception as e:
        logger("No se pudo leer datadir del repo {0}: {1}".format(repo_id, e))
    return None


def _ek_find_addon_version_in_index(addons_xml_text, addon_id):
    for pattern in (
        r'<addon[^>]*\bid="' + re.escape(addon_id) + r'"[^>]*\bversion="([^"]+)"',
        r'<addon[^>]*\bversion="([^"]+)"[^>]*\bid="' + re.escape(addon_id) + r'"',
    ):
        m = re.search(pattern, addons_xml_text)
        if m:
            return m.group(1)
    return None


def _ek_wait_addon_installed(addon_id, friendly_name):
    bg = xbmcgui.DialogProgressBG()
    bg.create(HEADING, "Esperando instalacion de {0}...".format(friendly_name))
    try:
        iters = (EK_ADDON_POLL_TIMEOUT_S * 1000) // EK_POLL_INTERVAL_MS
        for i in range(iters):
            if _ek_addon_is_installed(addon_id):
                return True
            xbmc.sleep(EK_POLL_INTERVAL_MS)
            bg.update(min(int((i + 1) * 100 / iters), 99), HEADING,
                      "Esperando instalacion de {0}...".format(friendly_name))
        return False
    finally:
        bg.close()


def _ek_wait_repo_ready(repo_id, dp):
    iters = (EK_REPO_POLL_TIMEOUT_S * 1000) // EK_POLL_INTERVAL_MS
    for i in range(iters):
        if dp.iscanceled():
            raise Exception("Cancelado por el usuario")
        if _ek_addon_is_installed(repo_id):
            return True
        # Sometimes the repo is left inactive after being extracted and has to be pushed
        if i in (4, 12, 24):
            xbmc.executebuiltin("EnableAddon({0})".format(repo_id))
        xbmc.sleep(EK_POLL_INTERVAL_MS)
    return False


def _ek_install_addon_zip_directly(addon_id, repo_id, friendly_name):
    # Plan B when InstallAddon() does not take. The datadir of the repo already installed is
    # read, the version is looked up in its addons.xml and the addon zip is fetched directly
    zip_path = None
    try:
        datadir = _ek_get_repo_datadir(repo_id)
        if not datadir:
            logger("Fallback ({0}): no se pudo obtener datadir de {1}".format(friendly_name, repo_id))
            return False
        # Repos with a local proxy (elementum serves on 127.0.0.1) publish no downloadable
        # datadir: if the proxy did not answer, fetching the zip by hand will not work either
        if "127.0.0.1" in datadir or "localhost" in datadir:
            logger("Fallback ({0}): datadir local, no aplica".format(friendly_name))
            return False

        try:
            addons_xml = _ek_download_text(datadir + "addons.xml")
        except Exception as e:
            logger("Fallback ({0}): no se pudo leer addons.xml: {1}".format(friendly_name, e))
            return False

        version = _ek_find_addon_version_in_index(addons_xml, addon_id)
        if not version:
            return False

        addon_zip_url = "{0}{1}/{1}-{2}.zip".format(datadir, addon_id, version)
        try:
            content = _ek_download_bytes(addon_zip_url, EK_MAX_ADDON_ZIP_BYTES, timeout=60)
        except Exception as e:
            logger("Fallback ({0}): no se pudo bajar el zip: {1}".format(friendly_name, e))
            return False

        addons_dir = xbmcvfs.translatePath("special://home/addons/")
        zip_path = os.path.join(xbmcvfs.translatePath("special://temp/"), "{0}-{1}.zip".format(addon_id, version))
        with open(zip_path, "wb") as f:
            f.write(content)

        _ek_extract_zip(zip_path, addons_dir)

        xbmc.executebuiltin("UpdateLocalAddons()")
        xbmc.sleep(1500)
        xbmc.executebuiltin("EnableAddon({0})".format(addon_id))
        xbmc.sleep(1500)
        for _ in range(20):
            if _ek_addon_is_installed(addon_id):
                return True
            xbmc.executebuiltin("EnableAddon({0})".format(addon_id))
            xbmc.sleep(EK_POLL_INTERVAL_MS)
        return _ek_try_recover_addon(addon_id) or _ek_addon_is_installed(addon_id)

    except Exception as e:
        logger("Fallback excepcion: {0}".format(e), 'error')
        return False

    finally:
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass


def _ek_notify_done(friendly_name):
    xbmcgui.Dialog().notification(HEADING, "{0} instalado correctamente".format(friendly_name),
                                  xbmcgui.NOTIFICATION_INFO, 4000)
    xbmc.executebuiltin("Container.Refresh")


def _ek_install_error(friendly_name, err):
    logger("Error instalando {0}: {1}".format(friendly_name, err), 'error')
    xbmcgui.Dialog().ok(
        "Error de instalacion",
        "No se pudo instalar {0} automaticamente.\n\nError: {1}\n\n"
        "Puede que necesites activar Origenes desconocidos en Ajustes.".format(friendly_name, err)
    )


def _ek_finish_install(addon_id, repo_id, friendly_name):
    # Waits for the installation; if it does not arrive, it tries to re-enable and finally
    # the fallback of downloading the zip directly
    if _ek_wait_addon_installed(addon_id, friendly_name):
        _ek_notify_done(friendly_name)
        return True
    if _ek_try_recover_addon(addon_id):
        _ek_notify_done(friendly_name)
        return True

    bg = xbmcgui.DialogProgressBG()
    bg.create(HEADING, "Instalacion automatica de {0} (alternativa)...".format(friendly_name))
    bg.update(50)
    try:
        ok = _ek_install_addon_zip_directly(addon_id, repo_id, friendly_name)
    finally:
        bg.close()

    if ok:
        _ek_notify_done(friendly_name)
        return True
    return False


# --- Repo mode (general case) ---------------------------------------------------------------

def _ek_install_repo_and_addon(addon_id, repo_id, repo_zip_url, friendly_name):
    # If the repo is already there it is not extracted again; touching it live gives trouble
    repo_already_present = _ek_addon_is_installed(repo_id)
    dp = xbmcgui.DialogProgress()
    dp.create(
        HEADING,
        "Descargando repositorio de {0}...".format(friendly_name) if not repo_already_present
        else "Instalando {0}...".format(friendly_name)
    )
    zip_path = None
    try:
        if not repo_already_present:
            dp.update(5, "Descargando repositorio...")
            content = _ek_download_bytes(repo_zip_url, EK_MAX_REPO_ZIP_BYTES)

            zip_path = os.path.join(xbmcvfs.translatePath("special://temp/"), "{0}.zip".format(repo_id))
            with open(zip_path, "wb") as f:
                f.write(content)

            dp.update(20, "Extrayendo repositorio...")
            _ek_extract_zip(zip_path, xbmcvfs.translatePath("special://home/addons/"))

            dp.update(35, "Registrando repositorio en Kodi...")
            xbmc.executebuiltin("UpdateLocalAddons()")
            if not _ek_wait_repo_ready(repo_id, dp):
                raise Exception("Kodi no registro el repositorio tras {0}s".format(EK_REPO_POLL_TIMEOUT_S))

            dp.update(55, "Activando repositorio...")
            xbmc.executebuiltin("EnableAddon({0})".format(repo_id))
            xbmc.sleep(1500)

        dp.update(65, "Actualizando indice del repositorio...")
        xbmc.executebuiltin("UpdateAddonRepos()")
        xbmc.sleep(3000)

        # The dialog has to be closed BEFORE InstallAddon() or it fights with Kodi's
        # native dialog
        dp.close()
        xbmcgui.Dialog().notification(HEADING, "Confirma la instalacion de {0}".format(friendly_name),
                                      xbmcgui.NOTIFICATION_INFO, 4000)
        xbmc.executebuiltin("InstallAddon({0})".format(addon_id))

        if _ek_finish_install(addon_id, repo_id, friendly_name):
            return True

        xbmcgui.Dialog().ok(
            HEADING,
            "El repositorio de {0} se instalo, pero la instalacion del addon no se completo.\n\n"
            "Para terminarla a mano:\nAddons - Instalar desde repositorio - {0} - Instalar".format(friendly_name)
        )
        return False

    except Exception as e:
        _ek_install_error(friendly_name, e)
        return False

    finally:
        try:
            dp.close()
        except Exception:
            pass
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except Exception:
                pass


# --- Official mode (Kodi's official repo, always present) -----------------------------------

def _ek_install_official(addon_id, friendly_name):
    dp = xbmcgui.DialogProgress()
    dp.create(HEADING, "Instalando {0} desde el repositorio oficial...".format(friendly_name))
    try:
        dp.update(30, "Actualizando indice del repositorio...")
        xbmc.executebuiltin("UpdateAddonRepos()")
        xbmc.sleep(2000)
        dp.close()

        xbmcgui.Dialog().notification(HEADING, "Confirma la instalacion de {0}".format(friendly_name),
                                      xbmcgui.NOTIFICATION_INFO, 4000)
        xbmc.executebuiltin("InstallAddon({0})".format(addon_id))

        if _ek_wait_addon_installed(addon_id, friendly_name) or _ek_try_recover_addon(addon_id):
            _ek_notify_done(friendly_name)
            return True

        xbmcgui.Dialog().ok(
            HEADING,
            "No se pudo instalar {0}.\n\nComprueba que el repositorio oficial de Kodi esta habilitado\n"
            "(Addons - Mis addons - Repositorios) e intentalo de nuevo.".format(friendly_name)
        )
        return False

    except Exception as e:
        _ek_install_error(friendly_name, e)
        return False

    finally:
        try:
            dp.close()
        except Exception:
            pass


# --- Embedded mode (repository shipped inside EKHorus, e.g. elementum) ----------------------

def _ek_install_embedded(addon_id, repo_id, friendly_name):
    dp = xbmcgui.DialogProgress()
    dp.create(HEADING, "Preparando {0}...".format(friendly_name))
    try:
        # 1. Ensure the repository is in place. If the user already has it, it is left alone:
        #    theirs may be newer or carry their own settings
        if not _ek_addon_dir_present(repo_id):
            dp.update(10, "Instalando el repositorio de {0}...".format(friendly_name))
            src = os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "repos", repo_id)
            dst = xbmcvfs.translatePath("special://home/addons/{0}/".format(repo_id))
            if not os.path.isdir(src):
                raise Exception("Falta el repositorio embebido {0}".format(repo_id))
            _ek_copytree(src, dst)
            xbmc.executebuiltin("UpdateLocalAddons()")
            if not _ek_wait_repo_ready(repo_id, dp):
                raise Exception("Kodi no registro el repositorio embebido")

        dp.update(40, "Activando el repositorio...")
        xbmc.executebuiltin("EnableAddon({0})".format(repo_id))
        xbmc.sleep(1500)
        xbmc.executebuiltin("UpdateAddonRepos()")

        # 2. Wait for the repo proxy to publish the addon. It is a service and starts
        #    asynchronously, so InstallAddon() too early finds nothing
        dp.update(60, "Esperando al repositorio de {0}...".format(friendly_name))
        proxy_iters = (EK_PROXY_POLL_TIMEOUT_S * 1000) // EK_POLL_INTERVAL_MS
        proxy_ready = False
        for _ in range(proxy_iters):
            if dp.iscanceled():
                raise Exception("Cancelado por el usuario")
            if _ek_addon_available_in_repos(addon_id):
                proxy_ready = True
                break
            xbmc.sleep(EK_POLL_INTERVAL_MS)
        dp.close()

        # 3. Install. If the proxy never got to publish, restarting Kodi fixes it
        if not proxy_ready:
            xbmcgui.Dialog().ok(
                HEADING,
                "El repositorio de {0} se instalo, pero su servicio aun no responde.\n\n"
                "Reinicia Kodi y vuelve a pulsar {0} para completar la instalacion.".format(friendly_name)
            )
            return False

        xbmcgui.Dialog().notification(HEADING, "Confirma la instalacion de {0}".format(friendly_name),
                                      xbmcgui.NOTIFICATION_INFO, 4000)
        xbmc.executebuiltin("InstallAddon({0})".format(addon_id))

        if _ek_wait_addon_installed(addon_id, friendly_name) or _ek_try_recover_addon(addon_id):
            _ek_notify_done(friendly_name)
            return True

        xbmcgui.Dialog().ok(
            HEADING,
            "No se pudo completar la instalacion de {0}.\n\n"
            "Reinicia Kodi e intentalo de nuevo, o instalalo desde\n"
            "Addons - Instalar desde repositorio - {0}.".format(friendly_name)
        )
        return False

    except Exception as e:
        _ek_install_error(friendly_name, e)
        return False

    finally:
        try:
            dp.close()
        except Exception:
            pass


# --- Dispatcher -----------------------------------------------------------------------------

def _ek_dispatch_install(entry):
    addon_id, repo_id, zip_url, _src, name, _plot, _icon, mode, _kind = entry
    if mode == "official":
        return _ek_install_official(addon_id, name)
    if mode == "embedded":
        return _ek_install_embedded(addon_id, repo_id, name)
    return _ek_install_repo_and_addon(addon_id, repo_id, zip_url, name)


def _ek_open_installed(entry):
    addon_id, _repo_id, _zip, _src, name, _plot, _icon, _mode, _kind = entry
    # Only plugins have an interface. A script.module.* (youtube-dl) cannot be opened
    if addon_id.startswith("plugin."):
        xbmcgui.Dialog().notification(HEADING, "Abriendo {0}...".format(name), xbmcgui.NOTIFICATION_INFO, 2000)
        xbmc.executebuiltin("RunAddon({0})".format(addon_id))
    else:
        xbmcgui.Dialog().notification(HEADING, "{0} ya esta instalado".format(name),
                                      xbmcgui.NOTIFICATION_INFO, 3000)


def _ek_manual_instructions(entry):
    _addon_id, _repo_id, _zip, source, name, _plot, _icon, mode, kind = entry

    if mode == "official":
        text = (
            "[B]Como instalar {0} a mano[/B]\n\n"
            "Viene del repositorio oficial de Kodi, no hace falta anadir ninguna fuente.\n\n"
            "1. Addons - Instalar desde repositorio - Repositorio oficial de Kodi\n\n"
            "2. Addons de {1} - {0} - Instalar".format(name, kind)
        )
    elif mode == "embedded":
        text = (
            "[B]Como instalar {0} a mano[/B]\n\n"
            "Su repositorio viaja dentro de EKHorus, no hace falta anadir ninguna fuente.\n\n"
            "1. Ajustes - Sistema - Addons - activa Origenes desconocidos\n\n"
            "2. Pulsa {0} en este menu: EKHorus copia el repositorio y espera a su servicio\n\n"
            "3. Si el servicio no responde, reinicia Kodi y vuelve a pulsar {0}\n\n"
            "4. Tambien puedes ir a Addons - Instalar desde repositorio - ElementumOrg repository "
            "- Addons de {1} - {0}".format(name, kind)
        )
    else:
        text = (
            "[B]Como instalar {0} a mano[/B]\n\n"
            "1. Ajustes - Sistema - Addons - activa Origenes desconocidos\n\n"
            "2. Ajustes - Explorador de archivos - Anadir fuente:\n   {1}\n\n"
            "3. Addons - Instalar desde un archivo zip - {0}\n   repository.xxx-x.x.x.zip\n\n"
            "4. Instalar desde repositorio - {0} - Addons de {2} - {0}".format(name, source, kind)
        )

    xbmcgui.Dialog().textviewer("Instrucciones - {0}".format(name), text)


def launch_by_id(addon_id):
    entry = _EK_BY_ID.get(addon_id)
    if not entry:
        logger("launch_by_id: addon desconocido {0}".format(addon_id))
        return

    name = entry[4]

    # If it is already installed, it is opened and that is that
    if _ek_addon_is_installed(addon_id):
        _ek_open_installed(entry)
        return

    # If it is there but disabled, re-enabling is enough
    if _ek_try_recover_addon(addon_id):
        xbmcgui.Dialog().notification(HEADING, "{0} reactivado correctamente".format(name),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
        xbmc.executebuiltin("Container.Refresh")
        return

    idx = xbmcgui.Dialog().select(
        "{0} - instalacion".format(name),
        ["Instalar automaticamente", "Ver instrucciones de instalacion manual"]
    )
    if idx == 0:
        if xbmcgui.Dialog().yesno(HEADING, "{0} no esta instalado.\n\nDescargar e instalar automaticamente?".format(name)):
            _ek_dispatch_install(entry)
    elif idx == 1:
        _ek_manual_instructions(entry)


# --- Menu -----------------------------------------------------------------------------------

def _ek_open_url(url, titulo, pregunta, aviso_android):
    abrir = xbmcgui.Dialog().yesno(
        titulo,
        '{0}\n\n[B]{1}[/B]\n\nAbrir en el navegador?'.format(pregunta, url),
        nolabel='Cerrar',
        yeslabel='Abrir navegador',
    )
    if not abrir:
        return

    if xbmc.getCondVisibility('System.Platform.Android'):
        xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.VIEW","","{0}")'.format(url))
        xbmcgui.Dialog().notification(HEADING, aviso_android, xbmcgui.NOTIFICATION_INFO, 2000)
    else:
        import webbrowser
        try:
            ok = webbrowser.open(url)
        except Exception:
            ok = False
        if not ok:
            xbmcgui.Dialog().ok(HEADING, 'No se pudo abrir el navegador.\n\nAccede a mano a:\n{0}'.format(url))


def open_web():
    _ek_open_url(
        'https://espatv.github.io',
        'EspaKodi en la web',
        'Todos los addons del ecosistema y la app, en un sitio:',
        'Abriendo la web...',
    )


def open_repo_unificado():
    _ek_open_url(
        'https://loiolo.io',
        'Repositorio Unificado',
        'Anade esta URL como fuente en Kodi para instalar los addons de EspaKodi:',
        'Abriendo repositorio...',
    )


def open_apk_latest():
    # The downloads in the APK menu are 32-bit and frozen on one version. Here the user is
    # sent to the web, which is where the 64-bit ones and the latest ones are
    _ek_open_url(
        'https://espakodi.github.io/apk/',
        'Ultima version EspaKodi APK',
        'Descarga la ultima version de la app EspaKodi, en 32 y en 64 bits:',
        'Abriendo descarga...',
    )


def open_guia():
    _ek_open_url(
        'https://espakodi.github.io/ekstreaming/',
        'Guia de EKHorus',
        'La guia explica los montajes habituales de AceStream y AceServe, el motor en otro '
        'equipo y el diagnostico con VLC:',
        'Abriendo la guia...',
    )


def instalar_si_falta(addon_id):
    """Makes sure an addon of the ecosystem is available. Returns True if it is.

    Unlike launch_by_id(), it does NOT open the addon when it is already installed: here
    only its existence matters, because the caller is going to carry on with its own
    business (the control panel, for one, just wants to toggle the redirection)."""
    entry = _EK_BY_ID.get(addon_id)
    if not entry:
        logger("instalar_si_falta: addon desconocido {0}".format(addon_id))
        return False

    if _ek_addon_is_installed(addon_id):
        return True

    name = entry[4]

    # It may be installed but disabled, and re-enabling is faster than reinstalling
    if _ek_try_recover_addon(addon_id):
        xbmcgui.Dialog().notification(HEADING, "{0} reactivado correctamente".format(name),
                                      xbmcgui.NOTIFICATION_INFO, 3000)
        return True

    idx = xbmcgui.Dialog().select(
        "{0} - instalacion".format(name),
        ["Instalar automaticamente", "Ver instrucciones de instalacion manual"]
    )
    if idx == 0:
        _ek_dispatch_install(entry)
    elif idx == 1:
        _ek_manual_instructions(entry)

    return _ek_addon_is_installed(addon_id)


_PLOT_APK_LATEST = (
    'Abre espakodi.github.io/apk en el navegador, que es donde estan siempre las ultimas '
    'versiones de la app EspaKodi, tanto de 32 bits (armeabi-v7a) como de 64 bits (arm64-v8a). '
    'Las descargas de "Descargar APKs" son solo de 32 bits y no se actualizan solas.'
)


_PLOT_REPO_UNIFICADO = (
    'Fuente para instalar todos los addons del ecosistema EspaKodi. '
    'Anade loiolo.io como fuente en Kodi para tener acceso al repositorio con '
    'EspaTV, EspaDaily, AtresDaily, StreamNinja, loiolog, Flow FavManager, '
    'TopZilla y loiolink en un solo sitio.'
)

_PLOT_PORTAL = (
    'Portal de EspaKodi: acceso a todos los addons del ecosistema y a la app EspaKodi '
    'lista para usar. Se abre en el navegador (espatv.github.io).'
)


def _ek_url(**kwargs):
    # EKHorus routes Items in base64, not query strings. Building it with urlencode the way
    # espadaily and atresdaily do would not work here
    return '%s?%s' % (sys.argv[0], Item(**kwargs).tourl())


def render_menu(handle):
    media_dir = _media_dir()
    fanart = _addon_fanart()

    li_web = xbmcgui.ListItem(label='EspaKodi en la web')
    li_web.setArt({'icon': os.path.join(media_dir, "portal.png"), 'fanart': fanart})
    li_web.getVideoInfoTag().setPlot(_PLOT_PORTAL)
    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=_ek_url(action='ek_open_web'),
        listitem=li_web,
        isFolder=False
    )

    li_repo = xbmcgui.ListItem(label='Repositorio Unificado')
    li_repo.setArt({'icon': os.path.join(media_dir, "info_repo.png"), 'fanart': fanart})
    li_repo.getVideoInfoTag().setPlot(_PLOT_REPO_UNIFICADO)
    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=_ek_url(action='ek_open_repo'),
        listitem=li_repo,
        isFolder=False
    )

    li_apk_web = xbmcgui.ListItem(label='Ultima version EspaKodi APK')
    li_apk_web.setArt({'icon': os.path.join(media_dir, "descargas_web.png"), 'fanart': fanart})
    li_apk_web.getVideoInfoTag().setPlot(_PLOT_APK_LATEST)
    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=_ek_url(action='ek_open_apk'),
        listitem=li_apk_web,
        isFolder=False
    )

    enabled_ids = _ek_enabled_ids()
    for titulo, entradas in _ek_bloques():
        # Kodi does not take inert rows in a plugin listing, so the separator is a normal
        # row with an empty action: default.py leaves it without opening anything
        li_sep = xbmcgui.ListItem(label="[COLOR FFD9A520]————  {0}  ————[/COLOR]".format(titulo))
        li_sep.setArt({"icon": os.path.join(media_dir, "separator.png"), "fanart": fanart})
        xbmcplugin.addDirectoryItem(
            handle=handle,
            url=_ek_url(action=''),
            listitem=li_sep,
            isFolder=False
        )

        for addon_id, _repo_id, _zip, _src, name, plot, fallback_icon, _mode, _kind in entradas:
            installed = addon_id in enabled_ids
            if installed:
                status = "[COLOR lime]Instalado[/COLOR]"
            elif _ek_addon_dir_present(addon_id):
                status = "[COLOR orange]Deshabilitado[/COLOR]"
            else:
                status = "[COLOR gray]No instalado[/COLOR]"

            fallback_path = os.path.join(media_dir, fallback_icon or "play_generic.png")
            icon = _ek_addon_icon(addon_id, fallback=fallback_path, installed=installed)

            li = xbmcgui.ListItem(label="{0} - {1}".format(name, status))
            li.setArt({"icon": icon, "fanart": fanart})
            li.getVideoInfoTag().setPlot(plot)
            xbmcplugin.addDirectoryItem(
                handle=handle,
                url=_ek_url(action='ek_launch', addon_id=addon_id),
                listitem=li,
                isFolder=False
            )

    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # The directory is NOT closed here: it is closed by cerrar_directorio() in default.py,
    # which is the one keeping count so endOfDirectory() is not called twice


# --- Own window -----------------------------------------------------------------------

_PLOT_SECCION = {
    'Addons de EspaKodi': 'Los addons del ecosistema EspaKodi. Cada uno hace lo suyo y '
                          'ninguno depende de los demás; instala solo los que vayas a usar.',
    'Dependencias y motores': 'Piezas que otros addons necesitan por debajo. No tienen menú '
                              'propio: se instalan y ya está.',
    'Otros': 'Lo que hay en el catálogo y no encaja en las secciones de arriba.',
}


def _ek_estado(addon_id, instalado):
    """(pill text, colour, hint) according to how the addon stands."""
    if instalado:
        return ui_common.color('Instalado', ui_common.TINTA_VERDE), 'on', 'Pulsa para abrirlo'

    if _ek_addon_dir_present(addon_id):
        return (ui_common.color('Deshabilitado', ui_common.ORO), 'gris',
                'Está puesto pero apagado')

    return ui_common.color('No instalado', ui_common.GRIS), 'gris', 'Pulsa para instalarlo'


def _ek_filas():
    media_dir = _media_dir()
    enabled_ids = _ek_enabled_ids()

    filas = [
        list_screen.Fila(clave='web', titulo='EspaKodi en la web',
                         pista='espatv.github.io',
                         icono=os.path.join(media_dir, 'portal.png'),
                         plot=_PLOT_PORTAL),
        list_screen.Fila(clave='repo', titulo='Repositorio Unificado',
                         pista='La fuente con todo el ecosistema',
                         icono=os.path.join(media_dir, 'info_repo.png'),
                         plot=_PLOT_REPO_UNIFICADO),
        list_screen.Fila(clave='apkweb', titulo='Última versión APK',
                         pista='32 y 64 bits, siempre al día',
                         icono=os.path.join(media_dir, 'descargas_web.png'),
                         plot=_PLOT_APK_LATEST),
    ]

    for titulo, entradas in _ek_bloques():
        filas.append(list_screen.Fila(clave='', titulo=titulo, sep=True,
                                      plot=_PLOT_SECCION.get(titulo, '')))

        for addon_id, _repo, _zip, _src, name, plot, icono, _modo, _tipo in entradas:
            instalado = addon_id in enabled_ids
            etiqueta, tinta, pista = _ek_estado(addon_id, instalado)
            fallback = os.path.join(media_dir, icono or 'play_generic.png')
            filas.append(list_screen.Fila(
                clave=addon_id, titulo=name, pista=pista,
                icono=_ek_addon_icon(addon_id, fallback=fallback, installed=instalado),
                pastilla=(etiqueta, tinta), plot=plot))

    return filas


def mostrar_ventana():
    """EspaKodi Addons in its own window. False if it could not be opened."""
    abrir_luego = list()

    def pulsar(fila):
        if fila.clave == 'web':
            open_web()
        elif fila.clave == 'repo':
            open_repo_unificado()
        elif fila.clave == 'apkweb':
            open_apk_latest()
        elif _ek_addon_is_installed(fila.clave):
            # An addon launched from underneath a modal stays behind it, so the window is
            # closed first and it is opened on leaving doModal().
            abrir_luego.append(fila.clave)
            return 'cerrar'
        else:
            instalar_si_falta(fila.clave)

        return None

    abierta = list_screen.mostrar(
        titulo='[COLOR FFFFB70F][B]EK[/B][/COLOR]Horus[COLOR FF8A97A5]   ·   [/COLOR]'
               'EspaKodi Addons',
        subtitulo='Todo el ecosistema',
        hacer_filas=_ek_filas,
        al_pulsar=pulsar,
        botones=(('EspaKodi en la web', open_web),
                 ('Repositorio', open_repo_unificado)),
        estado='Pulsa un addon para abrirlo, o para instalarlo si te falta')

    for addon_id in abrir_luego:
        _ek_open_installed(_EK_BY_ID[addon_id])

    return abierta

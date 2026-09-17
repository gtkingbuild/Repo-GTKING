# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# EKHorus by RubénSDFA1laberot, based on Horus by Caperucitaferoz and previous work by:
# - Enen92 (https://github.com/enen92)
# - Joian (https://github.com/jonian)
#
# Thanks to those who have collaborated in any way, especially to:
# - @Canna_76
# - @AceStreamMOD (https://t.me/AceStreamMOD)
# - @luisma66 (tester raspberry)
# - logon84 (thanks from RubénSDFA1laberot
#   for ass:// links, reading from txt and Pastebin)
#
# This file is part of EKHorus for Kodi
#
# EKHorus for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Changes in this Horus Mod over Caperucitaferoz's original 1.1.9 (see the credits above):
# - ass:// links (resolved by DNS over elcano.top and decoded from base64/gzip, nested lists included).
# - Direct text search on acestreamsearch.net and search-ace.stream.
# - Several sources at once, separating the addresses with ; (merges and drops duplicates).
# - New list formats: pastebin/.txt, elcano and vercel.app / netlify.app pages.
# - A second selectable engine.
# - QR code of the acestream:// link as the item cover art.
# - Listitems with the modern getVideoInfoTag API and the manual ID accepting a 40-character hash.
#-------------------------------------------------------------------------------

from lib.utils import *
import base64
import gzip
import json

from lib import ui_common
from acestream.engine import Engine
from acestream.stream import Stream

error_flag = False


def plugin_handle():
    """Kodi directory handle, or -1 if the addon was not called as a plugin."""
    try:
        return int(sys.argv[1])
    except (IndexError, ValueError):
        return -1


_directorio_cerrado = False

def cerrar_directorio(succeeded=True, update=False, cache=False):
    """Closes the Kodi directory exactly once, if there is one at all.

    When another addon calls us with PlayMedia (that is how StreamNinja does it),
    Kodi gives us a handle and waits for an answer: if the script ends without
    giving one, it throws a "playback failed" over the video that is already
    opening. It is easy to forget in some exit branch, so it is centralised here."""
    global _directorio_cerrado

    handle = plugin_handle()
    if handle < 0 or _directorio_cerrado:
        return

    _directorio_cerrado = True
    xbmcplugin.endOfDirectory(handle=handle, succeeded=succeeded,
                              updateListing=update, cacheToDisc=cache)


class OSD(object):
    def __init__(self, stats):
        self.showing = False
        self.window = xbmcgui.Window(12901)
        self.stats = stats

        viewport_w, viewport_h = self._get_skin_resolution() #(1280, 720)
        posX = viewport_w - 305
        posY = 75

        window_w = 300
        window_h = 250
        font_max = 'font13'
        font_min = 'font10'

        # Background
        self.horus_background = xbmcgui.ControlImage(x=posX, y=posY, width=window_w, height=window_h,
                                                     filename=os.path.join(runtime_path, 'resources', 'media' , 'background.png'))
        # icon
        self.horus_icon = xbmcgui.ControlImage(x=posX + 25, y=posY + 15, width=38, height=28,
                                               filename=os.path.join(runtime_path, 'resources', 'media' , 'acestreamlogo.png'))
        # title
        self.horus_title = xbmcgui.ControlLabel(x=posX + 78, y=posY + 13, width=window_w - 10, height=30,
                                                label="Horus", font=font_max, textColor='0xFFEB9E17')
        # sep
        self.horus_sep1 = xbmcgui.ControlImage(x=posX + 5, y=posY + 55, width=window_w - 10, height=1,
                                               filename=os.path.join(runtime_path, 'resources', 'media', 'separator.png'))
        # Stats
        self.horus_status = xbmcgui.ControlLabel(x=posX + 25, y=posY + 80, width=window_w - 10, height=30, font=font_min, label=translate(30009) % '')
        self.horus_speed_down = xbmcgui.ControlLabel(x=posX + 25, y=posY + 100, width=window_w - 10, height=30, font=font_min, label=translate(30010) % 0)
        self.horus_speed_up = xbmcgui.ControlLabel(x=posX + 25, y=posY + 120, width=window_w - 10, height=30, font=font_min, label=translate(30011) % 0)
        self.horus_peers = xbmcgui.ControlLabel(x=posX + 25, y=posY + 140, width=window_w - 10, height=30, font=font_min, label=translate(30012) % 0)
        self.horus_downloaded = xbmcgui.ControlLabel(x=posX + 25, y=posY + 170, width=window_w - 10, height=30, font=font_min, label=translate(30013) % 0)
        self.horus_uploaded = xbmcgui.ControlLabel(x=posX + 25, y=posY + 190, width=window_w - 10, height=30, font=font_min, label=translate(30014) % 0)

        # sep
        self.horus_sep2 = xbmcgui.ControlImage(x=posX + 5, y=posY + window_h - 30, width=window_w - 10, height=1,
                                               filename=os.path.join(runtime_path, 'resources', 'media', 'separator.png'))

    def update(self,**kwargs):
        if self.showing:
            status = {'dl':translate(30007), 'prebuf': translate(30008) %(self.stats.progress) + '%'}
            self.horus_status.setLabel(translate(30009) % status.get(self.stats.status, self.stats.status))
            self.horus_speed_down.setLabel(translate(30010) % self.stats.speed_down)
            self.horus_speed_up.setLabel(translate(30011) % self.stats.speed_up)
            self.horus_peers.setLabel(translate(30012) % self.stats.peers)
            self.horus_downloaded.setLabel(translate(30013) % (self.stats.downloaded // 1048576))
            self.horus_uploaded.setLabel(translate(30014) % (self.stats.uploaded // 1048576))

    def show(self):
        self.window.addControl(self.horus_background)
        self.window.addControl(self.horus_icon)
        self.window.addControl(self.horus_title)
        self.window.addControl(self.horus_sep1)
        self.window.addControl(self.horus_status)
        self.window.addControl(self.horus_speed_down)
        self.window.addControl(self.horus_speed_up)
        self.window.addControl(self.horus_peers)
        self.window.addControl(self.horus_downloaded)
        self.window.addControl(self.horus_uploaded)
        self.window.addControl(self.horus_sep2)
        self.showing = True

    def hide(self):
        self.showing = False
        self.window.removeControl(self.horus_background)
        self.window.removeControl(self.horus_icon)
        self.window.removeControl(self.horus_title)
        self.window.removeControl(self.horus_sep1)
        self.window.removeControl(self.horus_status)
        self.window.removeControl(self.horus_speed_down)
        self.window.removeControl(self.horus_speed_up)
        self.window.removeControl(self.horus_peers)
        self.window.removeControl(self.horus_downloaded)
        self.window.removeControl(self.horus_uploaded)
        self.window.removeControl(self.horus_sep2)

    def _get_skin_resolution(self):
        # If the skin does not declare a resolution (or its xml cannot be read), it
        # falls back to the classic 1280x720: a slightly misplaced OSD is better than
        # blocking playback altogether, which is what used to happen.
        try:
            import xml.etree.ElementTree as ET
            skin_path = translatePath("special://skin/")
            tree = ET.parse(os.path.join(skin_path, "addon.xml"))
            try: res = tree.findall("./res")[0]
            except IndexError: res = tree.findall("./extension/res")[0]
            return int(res.attrib["width"]), int(res.attrib["height"])
        except Exception as e:
            logger("_get_skin_resolution: %s" % e, 'error')
            return 1280, 720

    def close(self):
        try:
            self.hide()
        except:
            pass


class MyPlayer(xbmc.Player):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MyPlayer, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        logger("MyPlayer init")
        self.total_Time = 0
        self.monitor = xbmc.Monitor()
        xbmc.Player().stop()
        while xbmc.Player().isPlaying() and not self.monitor.abortRequested():
            self.monitor.waitForAbort(1)


    def playStream(self, stream, title='', iconimage='', plot='', init_time=0.0):
        self.AVStarted = False
        self.is_active = True
        self.init_time = float(init_time)
        # If the video dies before the first valid getTime(), current_time
        # was read without ever having been assigned (AttributeError).
        self.current_time = 0.0
        self.osd = OSD(stream.stats)

        status = 'failed'

        listitem = xbmcgui.ListItem()
        infotag = listitem.getVideoInfoTag()
        # The engine may give neither filename nor id (and the caller, no title):
        # setTitle(None) raises TypeError and playback died here, mute.
        title = title or stream.filename or stream.id or ADDON_NAME
        infotag.setTitle(title)
        if plot:
            infotag.setPlot(plot)
        art = {'icon': iconimage if iconimage else os.path.join(runtime_path, 'resources', 'media', 'icono_aces_horus.png')}
        listitem.setArt(art)

        self.play(stream.playback_url, listitem)
        cerrar_directorio(succeeded=False, update=True)
        xbmc.executebuiltin('Dialog.Close(all,true)')

        show_stat = False
        while self.is_active and not self.monitor.abortRequested():
            try:
                self.current_time = self.getTime()
            except:
                pass
            if get_setting("show_osd"):
                """if show_stat:
                    # update stat
                    self.osd.update()"""

                if not show_stat and xbmc.getCondVisibility('Window.IsActive(videoosd)'):
                    #show windows OSD
                    self.osd.show()
                    stream.connect('stats::updated', self.osd.update)
                    show_stat = True

                elif not xbmc.getCondVisibility('Window.IsActive(videoosd)'):
                    # hide windows OSD
                    if self.osd.showing:
                        self.osd.hide()
                        stream.disconnect('stats::updated')
                    show_stat = False

            self.monitor.waitForAbort(1)

        if self.AVStarted:
            if self.current_time > 180:
                add_historial({'infohash': stream.infohash,
                                'title': title,
                                'icon': iconimage if iconimage else '',
                                'plot': plot})
                if stream.id:
                    set_setting("last_id", stream.id)

            if self.current_time >= 0.9 * self.total_Time:
                status = 'finished'
            else:
                status = 'stopped'

            clear_cache()

        # Outside the if on purpose: if the OSD did get shown and playback never
        # started, its controls stayed stuck in the video window.
        osd = getattr(self, 'osd', None)
        if osd:
            osd.close()

        return status

    def onAVStarted(self):
        logger("PLAYBACK AVSTARTED")
        self.AVStarted = True
        self.total_Time = self.getTotalTime()
        if self.init_time:
            self.seekTime(self.init_time)

    def onPlayBackEnded(self):
        logger("PLAYBACK ENDED") # Network drop or end of video
        self.is_active = False

    def onPlayBackStopped(self):
        logger("PLAYBACK STOPPED") # Stopped by the user, or never started because of http 429
        self.is_active = False

    def onPlayBackError(self):
        logger("PLAYBACK ERROR")
        self.is_active = False

    def onPlayBackStarted(self):
        logger("PLAYBACK STARTED")

    def kill(self):
        logger("Play Kill")
        self.is_active = False


HISTORIAL_MAX = 20

def historial_path():
    return os.path.join(data_path, "historial.json")


def get_historial():
    historial = list()
    settings_path = historial_path()
    if os.path.isfile(settings_path):
        try:
            historial = load_json_file(settings_path)
        except Exception:
            logger("Error load_file", "error")

    return historial if isinstance(historial, list) else list()


def add_historial(contenido):
    # With no infohash the entry can neither be played again nor deleted:
    # it would be a zombie row in the list. Better not to save it.
    if not contenido.get('infohash'):
        logger("add_historial: sin infohash, no se guarda", 'error')
        return

    # If it was already there, it is reinserted at the top: last watched goes first.
    historial = [i for i in get_historial() if i.get('infohash') != contenido['infohash']]
    historial.insert(0, contenido)

    try:
        dump_json_file(historial[:HISTORIAL_MAX], historial_path())
    except Exception as e:
        # The history is incidental: if it cannot be written (full disk, permissions)
        # it is logged, but the end of playback is not aborted.
        logger("add_historial: %s" % e, 'error')


def del_historial(infohash=None):
    if infohash:
        historial = [i for i in get_historial() if i.get('infohash') != infohash]
    else:
        historial = list()

    try:
        dump_json_file(historial, historial_path())
    except Exception as e:
        logger("del_historial: %s" % e, 'error')


CACHE_DIR_NAME = '.acestream_cache'
# On Windows the engine calls the same thing by another name.
CACHE_DIR_NAMES = (CACHE_DIR_NAME, '_acestream_cache_')
# Margin before emptying the cache of an engine other than the one just used.
CACHE_IDLE_SECONDS = 60
# Cap on the scan, in case the tree is odd and returns a wild list.
CACHE_MAX_DIRS = 8


def is_cache_dir(path):
    """Fence around the deletion.

    The .ACEStream folders around it are the engine profile, with its acestream.conf
    and its database inside. Emptying them would leave it unconfigured, so only the
    cache folder proper is touched."""
    return os.path.basename(os.path.normpath(path)) in CACHE_DIR_NAMES


def cache_candidates():
    """(engine, path) pairs where the cache may be, per platform.

    On Android BOTH engines are ALWAYS returned. Before, only the one selected at that
    moment was looked at, so for whoever alternated between them the cache of the one
    being dropped grew without limit."""
    paths = list()
    install = get_setting("install_acestream")
    install = install if isinstance(install, str) and os.path.isdir(install) else None

    if system_platform == "windows":
        drive = os.getenv("SystemDrive") or "C:"
        paths.append((ENGINE_ACESTREAM, os.path.join(drive + os.sep, '_acestream_cache_')))
        for var in ("LOCALAPPDATA", "APPDATA", "USERPROFILE"):
            base = os.getenv(var)
            if base:
                paths.append((ENGINE_ACESTREAM, os.path.join(base, 'ACEStream', 'cache', CACHE_DIR_NAME)))

    elif system_platform == "linux":
        home = os.getenv("HOME")
        if home:
            paths.append((ENGINE_ACESTREAM, os.path.join(home, '.ACEStream', 'cache', CACHE_DIR_NAME)))
            paths.append((ENGINE_ACESTREAM, os.path.join(home, '.ACEStream', CACHE_DIR_NAME)))

    else:
        # node is today's official app package (checked in September 2026 against 3.2.22);
        # engine is the old one, and media and core are the ones in between, with their
        # .atv variants for Android TV. All are tried because which one exists depends on
        # the app the user has installed, and node goes first as the most likely.
        paquetes = (
            (ENGINE_ACESTREAM, 'org.acestream.node'),
            (ENGINE_ACESTREAM, 'org.acestream.node.atv'),
            (ENGINE_ACESTREAM, 'org.acestream.engine'),
            (ENGINE_ACESTREAM, 'org.acestream.media'),
            (ENGINE_ACESTREAM, 'org.acestream.media.atv'),
            (ENGINE_ACESTREAM, 'org.acestream.core'),
            (ENGINE_ACESTREAM, 'org.acestream.core.atv'),
            (ENGINE_ACESERVE, ENGINE_ACESERVE),
        )

        for engine, paquete in paquetes:
            # With scoped storage from Android 10 onwards, an app only writes under
            # Android/data. This is the path the current official app really uses, checked
            # on an Android 11: the old shape below is no longer created by anybody, but
            # it is kept for the devices still on Android 9.
            paths.append((engine,
                          f'/storage/emulated/0/Android/data/{paquete}/files/.ACEStream/{CACHE_DIR_NAME}'))
            paths.append((engine,
                          f'/storage/emulated/0/{paquete}/files/.ACEStream/{CACHE_DIR_NAME}'))
            paths.append((engine,
                          f'/storage/emulated/0/{paquete}/.ACEStream/{CACHE_DIR_NAME}'))

    if install:
        paths.append((ENGINE_ACESTREAM, os.path.join(install, CACHE_DIR_NAME)))
        paths.append((ENGINE_ACESTREAM, os.path.join(install, 'data', CACHE_DIR_NAME)))

    paths.append((ENGINE_ACESTREAM, os.path.join(data_path, CACHE_DIR_NAME)))

    # normpath: several came with a trailing slash and join produced double separators.
    return [(engine, os.path.normpath(path)) for engine, path in paths]


def find_cache_dirs(root, max_depth=4):
    """All the caches under 'root', bounding the depth.

    The original version did os.walk() from the root of the disk at the end of every
    playback, and on top of that kept only the first one it found."""
    encontradas = list()

    if not root or not os.path.isdir(root):
        return encontradas

    root = os.path.abspath(root)
    base_depth = root.rstrip(os.sep).count(os.sep)

    for dirpath, dirnames, _filenames in os.walk(root):
        # It is checked first and pruned afterwards: the other way round, a cache sitting
        # exactly at the limit level was never looked at.
        if is_cache_dir(dirpath):
            encontradas.append(dirpath)
            dirnames[:] = []  # there is no cache inside a cache
        elif dirpath.rstrip(os.sep).count(os.sep) - base_depth >= max_depth:
            dirnames[:] = []

        if len(encontradas) >= CACHE_MAX_DIRS:
            break

    return encontradas


def cache_last_write(path):
    """When the cache was last written to.

    The folder mtime is not enough, as it only changes when entries are created or
    deleted and not when writing inside a file that already exists. A cache in full
    use can look idle if only that is looked at."""
    ultimo = os.path.getmtime(path)

    try:
        with os.scandir(path) as entradas:
            for entrada in entradas:
                ultimo = max(ultimo, entrada.stat().st_mtime)
    except OSError as e:
        logger(f"cache_last_write: {path}: {e}", 'error')

    return ultimo


def purge_cache_dir(path):
    """Empties the contents of a cache, never the folder itself.

    Returns how many items it deleted."""
    if not is_cache_dir(path) or not os.path.isdir(path) or os.path.islink(path):
        logger(f"purge_cache_dir: no es una cache, no se toca: {path}", 'error')
        return 0

    borrados = 0
    dirnames, filenames = xbmcvfs.listdir(path)

    for name in filenames:
        try:
            if xbmcvfs.delete(os.path.join(path, name)):
                borrados += 1
        except Exception as e:
            logger(f"purge_cache_dir: {name}: {e}", 'error')

    for name in dirnames:
        sub = os.path.join(path, name)
        try:
            # rmdir with force also deletes whatever is inside. Before, only the loose
            # files were walked and the pieces in subfolders were left behind.
            if not os.path.islink(sub) and xbmcvfs.rmdir(sub, True):
                borrados += 1
        except Exception as e:
            logger(f"purge_cache_dir: {name}: {e}", 'error')

    return borrados


def clear_cache():
    inicio = time.time()

    try:
        recordadas = get_setting("acestream_cachefolder", None)
        # A single path used to be stored as text; now it is the list of all of them.
        if isinstance(recordadas, str):
            recordadas = [recordadas] if recordadas else list()
        elif not isinstance(recordadas, list):
            recordadas = list()

        activo = active_engine()

        # The candidates go first. That way a remembered path left stale by an engine
        # change can no longer hide the good one, which is what made the cache of the
        # wrong engine be cleaned every time.
        objetivos = dict()
        for engine, path in cache_candidates():
            if os.path.isdir(path):
                objetivos.setdefault(path, engine)
        for path in recordadas:
            if isinstance(path, str) and os.path.isdir(path):
                objetivos.setdefault(path, None)

        if not objetivos:
            # Last resort and the only expensive route: search under the engine folder
            # and the addon one. Never over the whole disk.
            install = get_setting("install_acestream")
            for root in (install if isinstance(install, str) else None, data_path):
                for path in find_cache_dirs(root):
                    objetivos.setdefault(path, None)
                if objetivos:
                    break

        if not objetivos:
            logger("clear_cache: cache no encontrada", "error")
            return

        # It is only saved when it changes: set_setting rewrites settings.xml and this
        # runs at the end of every playback.
        encontradas = sorted(objetivos)
        if encontradas != sorted(p for p in recordadas if isinstance(p, str)):
            set_setting("acestream_cachefolder", encontradas)

        for path, engine in objetivos.items():
            # The one of the engine just used is always emptied. The other one only if it has
            # been quiet for a while: AceServe may be serving a phone on the network while
            # Kodi plays through AceStream, and emptying it cuts their video off.
            if engine is not None and engine != activo:
                try:
                    if time.time() - cache_last_write(path) <= CACHE_IDLE_SECONDS:
                        logger(f"clear_cache: {path} parece en uso, se deja")
                        continue
                except OSError:
                    pass

            logger(f"clear_cache: {purge_cache_dir(path)} elementos en {path}")

        logger(f"clear_cache: {len(objetivos)} carpetas en {time.time() - inicio:.1f}s")

    except Exception as e:
        logger(f"error clear_cache: {e}", "error")


def opciones_transcode():
    """Audio parameters for the engine, per the setting. Empty if nothing needs touching.

    Only /ace/manifest.m3u8 accepts them, which means turning them on switches playback
    from MPEG-TS to HLS. That adds some latency on live, and that is why the setting comes
    off: it is turned on when a channel sounds bad, not just in case."""
    modo = get_setting('transcode_audio', 0)

    if modo == 1:
        return {'transcode_ac3': 1}
    if modo == 2:
        return {'transcode_audio': 1}

    return dict()


def elegir_fichero(ficheros):
    """Index of the file the user picks, or None if they cancel.

    The index is the one the engine gave, never the position in the list: the numbers have
    gaps because the engine keeps the torrent's own and skips whatever is not media, and a
    made-up one opens no session."""
    if len(ficheros) == 1:
        return ficheros[0]['index']

    elegido = xbmcgui.Dialog().select(translate(30110),
                                      [f['filename'] for f in ficheros])

    return None if elegido < 0 else ficheros[elegido]['index']


def read_torrent(torrent, headers=None):
    import bencodepy
    import hashlib

    infohash = None

    try:
        if torrent.lower().startswith('http'):
            torrent_file = http_get_bytes(torrent, headers)

        elif os.path.isfile(torrent):
            with open(torrent, "rb") as f:
                torrent_file = f.read()

        else:
            logger("read_torrent: origen no valido %s" % torrent, 'error')
            return None

        metainfo = bencodepy.decode(torrent_file)
        infohash = hashlib.sha1(bencodepy.encode(metainfo[b'info'])).hexdigest()
        logger(infohash)

    except Exception as e:
        logger(e, 'error')

    return infohash


def acestreams(id=None, url=None, infohash=None, title="", iconimage="", plot="",
               desde_motor=False):
    #logger(id)
    global error_flag
    # Hygiene: an error from an earlier invocation in the same process must not
    # contaminate this one (it matters if reuselanguageinvoker is ever enabled).
    error_flag = False
    player = None
    stream = None
    engine = None
    d = None
    cmd_stop_acestream = None
    acestream_executable = None
    motor_lanzado = False

    #url = 'http://dl.acestream.org/sintel/sintel.torrent'
    #url = 'https://files.grantorrent.nl/torrents/peliculas/Otra-vuelta-de-tuerca-(The-Turning)-(2020).avi53.torrent'
    #infohash = 'eebd63aa0a5edc49b253fc5741e49e32961d0f4f'


    # check arguments
    if infohash:
        url = id = None
    elif url:
        infohash = id = None
    else:
        regex = re.compile(r'[0-9a-f]{40}\Z',re.I)
        if not regex.match(id):
            xbmcgui.Dialog().ok(HEADING, translate(30015))
            return

    if not server.available:
        # If the engine installation failed or was cancelled, the setting is left
        # empty (None or False): without this normalisation, os.path.join raised
        # TypeError outside of any try. With an empty path the executable is left as
        # None, which ends in the friendly "we could not start it" dialog.
        install_path = get_setting("install_acestream")
        if not isinstance(install_path, str):
            install_path = ''

        # Create an engine instance. The command ALWAYS goes as a list: passed as a
        # string, a path with spaces (C:\Users\Juan Perez\...) is split in half when
        # running it and the engine never starts.
        if system_platform == "windows":
            if install_path:
                acestream_executable = [os.path.join(install_path, 'ace_engine.exe')]

        elif system_platform == "linux":
            if arquitectura == 'x86':
                if root:
                    # LibreElec x86
                    if install_path:
                        acestream_executable = [os.path.join(install_path, 'acestream_chroot.start')]
                        cmd_stop_acestream = ["pkill", "acestream"]
                else:
                    # Ubuntu, arch Linux, fedora, mint etc
                    if os.path.exists('/snap/acestreamplayer'):
                        acestream_executable = ['snap', 'run', 'acestreamplayer.engine']
                        cmd_stop_acestream = ["pkill", "acestream"]
                    else:
                        xbmcgui.Dialog().ok(HEADING,translate(30027))
                        return

            elif arquitectura == 'arm' and not root:
                try:
                    data = ''
                    with open("/etc/os-release") as f:
                        data = ensure_str(f.read())
                    if install_path and re.search('osmc|openelec|raspios|raspbian', data, re.I):
                        # osmc, openelec, raspios and raspbian
                        acestream_executable = ['sudo', os.path.join(install_path, 'acestream.start')]
                        cmd_stop_acestream = ['sudo', os.path.join(install_path, 'acestream.stop')]
                except: pass

            elif install_path:
                # LibreELEC, coreElec , alexelec, etc...
                acestream_executable = [os.path.join(install_path, 'acestream.start')]
                cmd_stop_acestream = [os.path.join(install_path, 'acestream.stop')]

        elif system_platform == 'android':
            AndroidActivity = android_engine_launch()
            # This used to be a yesno. Whoever presses a link has already said they want
            # to play it, so asking them again only gets in the way. The one thing worth
            # telling them is that Kodi is going to the background, and for that a notice
            # that does not block the way is enough.
            xbmcgui.Dialog().notification(HEADING, translate(30090), icon_path, 4000)
            logger("Abriendo " + AndroidActivity)
            xbmc.executebuiltin(AndroidActivity)
            motor_lanzado = True

        logger("acestream_executable= %s" % acestream_executable)

        if cmd_stop_acestream:
            set_setting("cmd_stop_acestream", cmd_stop_acestream)

        if acestream_executable and not server.available:
            engine = Engine(acestream_executable)

        elif not acestream_executable and system_platform != 'android':
            logger("plataforma desconocida: %s" % system_platform)
            if not xbmcgui.Dialog().yesno(HEADING, translate(30016), nolabel=translate(30017), yeslabel=translate(30018)):
                return

    try:
        # Waiting for the engine goes BEFORE the external player. That branch sends the
        # video to another app and leaves, so without waiting here VLC gets an address
        # where nobody is listening yet. The yesno that used to be here was acting as a
        # wait without meaning to, and removing it uncovered the race.
        if not acestream_executable or system_platform == 'android':
            espera = get_setting("time_limit", 30)
            if motor_lanzado:
                # If we are the ones who opened the app, the user is outside Kodi and needs
                # room to come back with Back. With the yesno the countdown started when they
                # answered; now it starts straight away, and with the default 30 seconds,
                # taking 40 to come back gave "engine not started" with the engine already
                # running.
                espera = max(ENGINE_LAUNCH_WAIT_MIN, espera * 2)

            timedown = time.time() + espera

            if not server.available:
                d = xbmcgui.DialogProgress()
                d.create(HEADING, translate(30033))

                while not d.iscanceled() and not server.available and time.time() < timedown and error_flag == False:
                    seg = int(timedown - time.time())
                    progreso = int((seg * 100) / espera)
                    line1 = translate(30033)
                    line2 = translate(30006) % seg
                    try:
                        d.update(progreso, line1, line2)
                    except:
                        d.update(progreso, '\n'.join([line1, line2]))
                    time.sleep(1)

            if not server.available:
                # Whoever cancels does not want explanations, they want out. With the notice
                # in a notification it made no difference, but these are modal dialogs now and
                # planting one after pressing Cancel is worse than saying nothing.
                cancelado = bool(d) and d.iscanceled()

                if d:
                    d.close()
                    d = None

                if not cancelado:
                    # If the port is taken but the API does not answer, something else has it.
                    # Both engines use the same one and the second is left out.
                    if server.ping():
                        xbmcgui.Dialog().ok(HEADING, translate_fmt(30089, server.port))
                    elif motor_lanzado:
                        # The intent does not report whether it opened anything. If on top of that
                        # nobody is listening, most likely there is no engine installed.
                        xbmcgui.Dialog().ok(HEADING, translate(30091))
                    else:
                        notification_error(translate(30019))

                raise Exception("accion cancelada o timeout")

        # There is an engine on the other side now, so now we can look at which one. It
        # goes before the external player because that branch leaves and never gets here.
        check_engine()

        # Channels from the catalogue and from the engine's list arrive with an infohash,
        # and the external player branch below demands an id. Without this conversion, on
        # Android they would play inside Kodi ignoring a setting that comes on by default
        # precisely because in there they give trouble. The engine returns the same
        # broadcast either way, checked, and they go over MPEG-TS like the rest.
        #
        # It is done HERE and not on pressing: the engine is already up and answers in
        # milliseconds. Doing it earlier cost up to ten seconds of mute wait when it was
        # switched off.
        if desde_motor and infohash and not id:
            content_id = server.get_content_id(infohash)
            if content_id:
                id, infohash = content_id, None
            else:
                logger('acestreams: no se pudo resolver el content_id, se sigue con el infohash')

        if id and system_platform == 'android' and get_setting("reproductor_externo"):
            if d:
                d.close()
                d = None
            if active_engine() == ENGINE_ACESERVE:
                # host and port come from the server, not from the raw settings: re-reading them
                # gave different addresses from the ones the rest of the addon uses (an ip_addr
                # with the port stuck on ended up as http://ip:6878:6878/).
                AndroidActivity = 'StartAndroidActivity("","android.intent.action.VIEW","video/mp4","http://%s:%s/ace/getstream?id=%s")' % (server.host, server.port, id)
            else:
                AndroidActivity = 'StartAndroidActivity("","org.acestream.action.start_content","","acestream:?content_id=%s")' % id
            logger("Abriendo " + AndroidActivity)
            xbmc.executebuiltin(AndroidActivity)
            return

        if not d:
            d = xbmcgui.DialogProgress()
            d.create(HEADING, translate(30033))
        timedown = time.time() + get_setting("time_limit", 30)

        if engine and not server.available:
            # Start engine if the local server is not available
            engine.connect(['error','error::subprocess'], notification_error)
            #engine.connect(['started', 'terminated'], notification_info)
            engine.start()

            # Wait for engine to start. All that matters is that the engine answers:
            # on OSMC/LibreELEC the .start is a launcher that starts the engine and
            # exits, so engine.running goes back to False and with the "or not
            # engine.running" the loop never ended, ran out of time and said "engine
            # not started" with the engine already working.
            while not d.iscanceled() and not server.available and time.time() < timedown and error_flag == False:
                seg = int(timedown - time.time())
                progreso = int((seg * 100) / get_setting("time_limit", 30))
                line1 = translate(30033)
                line2 = translate(30006) % seg
                try:
                    d.update(progreso, line1, line2)
                except:
                    d.update(progreso, '\n'.join([line1, line2]))

                time.sleep(1)

            if d.iscanceled() or time.time() >= timedown or error_flag == True: # Timed out or cancelled
                if engine.running:
                    engine.stop()
                d.close()
                if time.time() >= timedown:
                    notification_error(translate(30019))
                raise Exception("accion cancelada o timeout")

        hls = False
        if id:
            # Start a stream using an acestream channel ID
            stream = Stream(server, id=id)
        elif url:
            # Start a stream using an url
            hls = True
            stream = Stream(server, url=url)
        else:
            # Start a stream using an acestream infohash
            hls = True
            stream = Stream(server, infohash=infohash)

        # The engine only accepts the audio parameters on manifest.m3u8, so asking for
        # them forces playback over to HLS. The setting comes off and its text says so.
        opciones = opciones_transcode()
        if opciones:
            hls = True

        stream.connect('error', notification_error)
        stream.connect(['started','stopped'], notification_info)
        stream.start(hls=hls, **opciones)

        # When the content has several media files and none is named, the engine answers
        # with the list instead of with the stream. Until now that answer was taken for an
        # empty success and the wait below sat looking at a state that never arrived, so a
        # torrent with several episodes always ended in "engine not started" with the
        # engine perfectly alive.
        if stream.media_files:
            if d:
                d.close()

            indice = elegir_fichero(stream.media_files)
            if indice is None:
                raise Exception("seleccion de fichero cancelada")

            d = xbmcgui.DialogProgress()
            d.create(HEADING, translate(30033))

            stream.start(hls=hls, _idx=indice, **opciones)

            # Retrying without _idx would only bring the list back again.
            if stream.media_files:
                raise Exception("el motor sigue pidiendo fichero")

        # Wait for stream to start
        timedown = time.time() + get_setting("time_limit")
        while not d.iscanceled() and time.time() < timedown and (not stream.status or stream.status != 'dl') and error_flag == False:
            if stream.status != 'prebuf':
                seg = int(timedown - time.time())
                progreso = int((seg * 100) / get_setting("time_limit"))
            else:
                progreso = stream.stats.progress
                timedown = time.time() + 100

            if not stream.status:
                line1 = translate(30034)
            elif stream.status == 'prebuf':
                line1 = translate(30008) %(progreso) + '%'
            elif stream.status == 'dl':
                line1 = translate(30007)
            else:
                line1 = stream.status

            line2 = translate(30010) % stream.stats.speed_down
            line3 = translate(30012) % stream.stats.peers
            try:
                d.update(progreso, line1, line2, line3)
            except:
                d.update(progreso, '\n'.join([line1, line2, line3]))

            time.sleep(0.25)

        d.close()
        if d.iscanceled() or time.time() >= timedown or error_flag == True:  # Timed out or cancelled
            if error_flag:
                raise Exception("error flag")
            else:
                raise Exception("accion cancelada o timeout")

        # Open a media player to play the stream
        player = MyPlayer()
        player.playStream(stream, title, iconimage, plot)

    except Exception as e:
        logger(e, 'error')
        # Without this, an error between create() and the first close() left the
        # progress dialog planted on the screen.
        try:
            if d: d.close()
        except: pass

    try:
        if player:
            player.kill()
    except: pass

    # Only if the stream got to start: stopping a stream that never started
    # asked for http://host/None and fired a second error notification.
    if stream and stream.command_url:
        stream.stop()

    # stop Engine
    if get_setting("stop_acestream", False) or get_setting("linux_id") == 'ubuntu':
        kill_process()


def notification_info(*args,**kwargs):
    transmitter = kwargs['class_name']
    msg = kwargs['event_name']

    logger("%s: %s" %(transmitter, msg))
    #xbmcgui.Dialog().notification('Acestream %s' % transmitter, msg, os.path.join(runtime_path, 'resources', 'media', 'icono_aces_horus.png'))


def notification_error(*args,**kwargs):
    global error_flag
    transmitter = kwargs.get('class_name', ADDON_NAME)
    event = kwargs.get('event_name','')
    # The engine may emit an error with no message: it must not blow up here.
    msg = str(args[0]) if args and args[0] else translate(30019)
    error_flag = True

    logger("Error in %s: %s" % (transmitter, msg))

    if event != 'error::subprocess':
        xbmcgui.Dialog().notification('Error Acestream %s' % transmitter, msg,
                                      os.path.join(runtime_path, 'resources', 'media', 'error.png'))


ENGINE_WARNED_PROP = 'ekhorus_engine_warned'

# Minimum margin when we are the ones opening the engine app: Kodi goes to the
# background and the user has to come back with Back.
ENGINE_LAUNCH_WAIT_MIN = 60


def check_engine():
    """Warns if an engine other than the chosen one answers on the port.

    Both engines use 6878 and cannot coexist. With AceServe starting on its own when
    Android boots, the addon ended up talking to it without knowing, and whoever had
    chosen AceStream did not understand why it was not working.

    It must not bring playback down: if something fails here, the video carries on."""
    try:
        detectado = detect_engine()
        elegido = active_engine()

        if not detectado or detectado == elegido:
            return detectado

        logger(f"check_engine: elegido {engine_name(elegido)}, contesta {engine_name(detectado)}")

        # The warning points at the "Motor ace" setting, which only exists on Android.
        # Elsewhere active_engine() always returns AceStream, so a remote engine that
        # turns out to be AceServe would raise a warning sending the user to check a
        # setting they do not have. It is still detected, because the channels menu needs
        # it, but it keeps quiet.
        if system_platform != 'android':
            return detectado

        # Only once per Kodi session. Repeating it on every link would be a punishment,
        # above all because playback is going to work anyway.
        window = xbmcgui.Window(10000)
        if not window.getProperty(ENGINE_WARNED_PROP):
            window.setProperty(ENGINE_WARNED_PROP, '1')
            xbmcgui.Dialog().notification(HEADING,
                                          translate_fmt(30088, engine_name(detectado), server.port),
                                          os.path.join(runtime_path, 'resources', 'media', 'error.png'),
                                          6000)

        return detectado

    except Exception as e:
        logger(f"check_engine: {e}", 'error')
        return None


QR_MAX_AGE_DAYS = 30


def limpiar_qr_viejos():
    """Deletes the QR PNGs that nobody is going to reuse.

    qr_poster() writes them in special://temp and until now nobody deleted them,
    so they piled up one per channel watched."""
    limite = time.time() - QR_MAX_AGE_DAYS * 86400

    try:
        with os.scandir(translatePath('special://temp')) as entradas:
            for entrada in entradas:
                if (entrada.name.startswith('ekhorus_qr_') and entrada.is_file()
                        and entrada.stat().st_mtime < limite):
                    os.remove(entrada.path)
    except Exception as e:
        # Cleaning up is incidental and cannot stop the menu from being painted.
        logger(f"limpiar_qr_viejos: {e}", 'error')


def icono(nombre):
    return os.path.join(runtime_path, 'resources', 'media', nombre)


def mainmenu():
    itemlist = list()

    # Only if they are enabled, because whoever does not use them has nothing to clean.
    if get_setting("show_qr_codes"):
        limpiar_qr_viejos()

    # With the classic interface, EspaKodi Addons and the APKs go back to being Kodi
    # folders instead of opening a window of their own, and the item has to say so.
    clasica = ui_common.clasica()

    # First row on purpose: it is an announcement, and the announcement nobody scrolls to
    # has not been made. It comes out of the menu when 2.0 ships.
    itemlist.append(Item(
        label=ui_common.color(translate(30130), ui_common.ORO),
        action='aviso_version',
        icon=icono('aviso.png'),
        plot=translate(30131)
    ))

    itemlist.append(Item(
        label= translate(30092),
        action='cuadro_mandos',
        icon=icono('cuadro.png'),
        plot=translate(30093)
    ))

    # No network condition on purpose: knowing whether there is a catalogue means asking
    # the engine, and mainmenu() cannot pay for a request against a switched-off ip_addr.
    # If there is no engine, the screen itself explains it and offers to start it.
    itemlist.append(Item(
        label=translate(30115),
        action='catalogo',
        icon=icono('motor.png'),
        plot=translate(30116),
        isFolder=clasica
    ))

    itemlist.append(Item(
        label= translate(30094),
        action='guia',
        icon=icono('guia.png'),
        plot=translate(30095)
    ))

    itemlist.append(Item(
        label= translate(30082),
        action='apk_menu',
        icon=icono('descargas.png'),
        plot=translate(30097),
        isFolder=clasica
    ))

    itemlist.append(Item(
        label= translate(30081),
        action='espakodi_addons',
        icon=icono('addons.png'),
        plot=translate(30098),
        isFolder=clasica
    ))

    if get_historial():
        itemlist.append(Item(
            label = translate(30037),
            action = 'historial',
            icon=icono('historial.png'),
            plot=translate(30101)
        ))

    # ping() instead of available(): a 2s TCP probe. With available(), a remote
    # ip_addr that is switched off blocked opening the menu for 10 seconds.
    if system_platform != 'android' and server.ping():
        itemlist.append(Item(
            label= translate(30036),
            action='kill',
            icon=icono('detener.png'),
            plot=translate(30102)
        ))

    itemlist.append(Item(
        label=translate(30128),
        action='experimental',
        icon=icono('experimental.png'),
        plot=translate(30129)
    ))

    itemlist.append(Item(
        label= translate(30021),
        action='open_settings',
        icon=icono('ajustes.png'),
        plot=translate(30103)
    ))

    # A green dot while nobody has been inside, which is how the other addons of the
    # house flag something worth a look. It goes out by itself on the first visit.
    aviso = '' if get_setting('universo_visto') else ui_common.color('●', ui_common.VERDE) + '  '
    itemlist.append(Item(
        label=aviso + translate(30096),
        action='universo',
        icon=icono('universo.png'),
        plot=translate(30104)
    ))

    return itemlist


def experimental_menu():
    """What is still being tried out, gathered behind one row.

    The three of them work, but each one asks something of the user that the rest of the
    menu does not: the web page needs another device on the same network, and the other
    two need an identifier or an address that has to come from somewhere else. Out in the
    main menu they made the addon look harder than it is."""
    return [
        Item(label=translate(30125),
             action='web',
             icon=icono('movil.png'),
             plot=translate(30126)),
        Item(label=translate(30020),
             action='play',
             icon=icono('play_generic.png'),
             plot=translate(30099)),
        Item(label=translate(30038),
             action='search',
             icon=icono('busqueda.png'),
             plot=translate(30100)),
    ]


# The APKs in the menu are 32-bit on purpose: they target Fire TV Stick and TV boxes,
# where getting a file onto the device is a nuisance. The explanation is in string 30075.
#
# The real list lives in a json in the repository the addon already publishes, so when
# the hosting gets taken down (archive.org darkened the whole item) it is fixed by
# editing that file, with no new release. This here is only the fallback.
APK_DOWNLOADS = (
    ('AceStreamEK-32bits_v3.apk',
     'https://github.com/espakodi/EKHorus/releases/download/apk/AceStreamEK-32bits_v3.apk', 30083),
    ('Aceserve-1.5.7-armeabi-v7a.apk',
     'https://github.com/espakodi/EKHorus/releases/download/apk/Aceserve-1.5.7-armeabi-v7a.apk', 30084),
    ('VLC-3.6.5-armeabi-v7a.apk',
     'https://github.com/espakodi/EKHorus/releases/download/apk/VLC-3.6.5-armeabi-v7a.apk', 30085),
    ('EspaKodi-Warp-0.0.2-armeabi-v7a.apk',
     'https://github.com/espakodi/EKHorus/releases/download/apk/EspaKodi-Warp-0.0.2-armeabi-v7a.apk', 30086),
)

# Two hostings of the same file: raw answers instantly after editing it and Pages
# holds up if raw is blocked on the user's network.
APK_MANIFEST_URLS = (
    'https://raw.githubusercontent.com/espakodi/EKHorus/main/apks.json',
    'https://espakodi.github.io/EKHorus/apks.json',
)
# Three seconds and not the ten of HTTP_TIMEOUT, because this blocks opening a menu.
APK_MANIFEST_TIMEOUT = 3
# This is not a security barrier; whoever controls the repository publishes the whole
# addon anyway. It protects against a typo when editing the manifest.
APK_ALLOWED_HOSTS = ('github.com', 'objects.githubusercontent.com',
                     'raw.githubusercontent.com', 'espakodi.github.io', 'archive.org')

_APK_MANIFEST_PROP = 'ekhorus_apk_manifest'
_APK_MANIFEST_FAILED = 'fail'


def _apk_entry(raw):
    """Normalises one manifest entry, or None if it cannot be used."""
    if not isinstance(raw, dict):
        return None

    url = raw.get('url') or ''
    if not isinstance(url, str) or not url.startswith('https://'):
        return None

    host = urllib_parse.urlparse(url).hostname or ''
    if host not in APK_ALLOWED_HOSTS:
        logger(f'apk manifest: dominio no permitido {host}', 'error')
        return None

    # basename(): without this an entry with '../' would write outside the folder
    # the user has chosen in the dialog.
    filename = os.path.basename(str(raw.get('filename') or ''))
    if not filename:
        return None

    label = raw.get('label')
    if not label:
        label_id = raw.get('label_id')
        label = translate(label_id) if isinstance(label_id, int) else ''

    return {'filename': filename,
            'url': url,
            'label': label or filename,
            'note': raw.get('note') or translate(30075),
            'sha256': str(raw.get('sha256') or '').lower()}


def _apk_entries_embedded():
    return [{'filename': filename, 'url': url, 'label': translate(label_id),
             'note': translate(30075), 'sha256': ''}
            for filename, url, label_id in APK_DOWNLOADS]


def apk_entries():
    """Entries of the APK menu, from the remote manifest or from the embedded fallback.

    Both the hit and the failure are cached. Every click reimports the module, so
    without storing the failure too, going in and out of the menu with a bad network
    chains one network wait per visit."""
    window = xbmcgui.Window(10000)
    cached = window.getProperty(_APK_MANIFEST_PROP)

    if cached == _APK_MANIFEST_FAILED:
        return _apk_entries_embedded()

    if cached:
        entries = parse_literal(cached)
        if isinstance(entries, list) and entries:
            return entries

    entries = list()
    for manifest_url in APK_MANIFEST_URLS:
        try:
            data = json.loads(http_get_text(manifest_url, timeout=APK_MANIFEST_TIMEOUT))
        except Exception as e:
            logger(f'apk manifest {manifest_url}: {e}', 'error')
            continue

        if not isinstance(data, list):
            logger(f'apk manifest {manifest_url}: se esperaba una lista', 'error')
            continue

        vistos = set()
        for raw in data:
            entry = _apk_entry(raw)
            # Two entries with the same name share the target file and the download
            # latch, so the second one is dropped.
            if entry and entry['filename'] not in vistos:
                vistos.add(entry['filename'])
                entries.append(entry)

        if entries:
            break

    # An empty list, or one where every entry is invalid, is as useless as a network
    # error, and has to end the same way: in the fallback.
    if not entries:
        window.setProperty(_APK_MANIFEST_PROP, _APK_MANIFEST_FAILED)
        return _apk_entries_embedded()

    window.setProperty(_APK_MANIFEST_PROP, dump_json(entries))
    return entries


def apk_menu():
    itemlist = list()

    for entry in apk_entries():
        itemlist.append(Item(
            label=entry['label'],
            action='download_apk',
            icon=icono('descargas.png'),
            filename=entry['filename'],
            apk_url=entry['url'],
            sha256=entry.get('sha256', ''),
            plot=entry.get('note') or translate(30075),
            isFolder=False
        ))

    itemlist.append(Item(
        label=translate(30074),
        action='apk_info',
        icon=icono('info.png'),
        plot=translate(30075),
        isFolder=False
    ))

    return itemlist


def entrar_en_lista(accion):
    """Enters the screen again asking for the classic list.

    Each menu row is painted as a folder or not according to the mode at painting time,
    and Kodi only gives a directory to write in to the ones that are folders. A row drawn
    before the classic interface was turned on arrives here with no directory, so one is
    asked for by entering again."""
    xbmc.executebuiltin('ActivateWindow(programs,%s?%s,return)'
                        % (sys.argv[0], Item(action=accion, clasico=1).tourl()))


def volver_a_lo_clasico(accion):
    """A window of our own could not open, so the classic list is painted.

    Without this you would have to remember the classic interface setting to get out of
    the jam, and an emergency exit you have to remember is no emergency exit."""
    logger('no se pudo abrir la ventana de %s, se abre la lista clasica' % accion, 'error')
    xbmcgui.Dialog().notification(HEADING, translate(30106), icon_path, 6000)
    entrar_en_lista(accion)


def apk_ventana():
    """Download APKs in its own window. False if it could not be opened."""
    from lib import list_screen

    def filas():
        # The folder may be a Kodi path and not a system one, so xbmcvfs is asked and
        # not os.path.
        carpeta = (default_apk_folder() or '').rstrip('/')
        salida = list()
        for entrada in apk_entries():
            bajado = bool(carpeta) and xbmcvfs.exists(carpeta + '/' + entrada['filename'])
            salida.append(list_screen.Fila(
                clave=entrada['filename'],
                titulo=entrada['label'],
                pista=entrada['filename'],
                icono=icono('descargas.png'),
                pastilla=(ui_common.color('Descargado', ui_common.TINTA_VERDE), 'on')
                         if bajado else None,
                plot=entrada.get('note') or translate(30075)))
        return salida

    porficheros = {e['filename']: e for e in apk_entries()}

    def pulsar(fila):
        entrada = porficheros.get(fila.clave)
        if entrada:
            download_apk(entrada['filename'], entrada['url'], entrada.get('sha256', ''))

    return list_screen.mostrar(
        titulo='[COLOR FFFFB70F][B]EK[/B][/COLOR]Horus[COLOR FF8A97A5]   ·   [/COLOR]'
               'Descargar APKs',
        subtitulo='Para Fire TV y TV box',
        hacer_filas=filas,
        al_pulsar=pulsar,
        botones=(('Última versión web', _apk_web),),
        estado='Se descargan a una carpeta que eliges tú. Instalarlos lo hace Android',
        pista='[B]OK[/B] descarga    ·    [B]Derecha[/B] lee    ·    [B]Atrás[/B] cierra')


def _apk_web():
    from lib import espakodi_installer
    espakodi_installer.open_apk_latest()


# DoH resolvers: if one is blocked on the user's network, the next one is tried.
DOH_RESOLVERS = [
    "https://dns.google/resolve?name={}&type=TXT",
    "https://cloudflare-dns.com/dns-query?name={}&type=TXT",
]
ASS_MAX_DEPTH = 10

def resolve_txt(name):
    for resolver in DOH_RESOLVERS:
        try:
            data = http_get_text(resolver.format(name), headers={'Accept': 'application/dns-json'})
            response = json.loads(data)
            if response.get("Answer"):
                return response["Answer"]
        except Exception as e:
            logger("resolve_txt %s: %s" % (resolver.split('/')[2], e), 'error')

    return list()


ass_ids = list()
def ass_decoder(ass_id_or_json, depth=0):
    global ass_ids
    itemlist = list()

    if depth > ASS_MAX_DEPTH:
        logger("ass_decoder: demasiados niveles de anidamiento", 'error')
        return itemlist

    try:
        json_data = json.loads(ass_id_or_json)
        is_json = isinstance(json_data, list)
    except Exception:
        is_json = False

    if not is_json:
        # The input is an ASS ID, not a json
        if ass_id_or_json in ass_ids:
            return itemlist

        ass_ids.append(ass_id_or_json)
        host = "{}.elcano.top".format(ass_id_or_json.replace("ass://", ""))

        for answer in resolve_txt(host):
            try:
                raw = answer.get("data", "").strip('"')
                if "H4sIAAAAAAAA" in raw:
                    json_data = gzip.decompress(base64.b64decode(raw)).decode("utf-8")
                else:
                    json_data = base64.b64decode(raw).decode("utf-8")

                itemlist = itemlist + ass_decoder(json_data, depth + 1)
            except Exception as e:
                logger("ass_decoder: respuesta TXT no valida: %s" % e, 'error')
    else:
        for jsitem in json_data:
            if not isinstance(jsitem, dict):
                continue

            if "subLinks" in jsitem:
                itemlist = itemlist + ass_decoder(json.dumps(jsitem["subLinks"]), depth + 1)
            elif "ref" in jsitem:
                itemlist = itemlist + ass_decoder(jsitem["ref"], depth + 1)
            elif "url" in jsitem and re.findall('([0-9a-f]{40})', jsitem["url"], re.I):
                chan_name = jsitem.get("name") or jsitem["url"]
                chan_id = re.findall('([0-9a-f]{40})', jsitem["url"], re.I)[0]
                itemlist.append(Item(label=chan_name ,action='play',id=chan_id))
            else:
                logger("ASS decoder: item ignorado: %s" % jsitem)

    return itemlist


def search_text(query):
    """Searches by text in the public acestream search engines."""
    itemlist = list()

    try:
        data = http_get_text("https://acestreamsearch.net/en/?q={}".format(urllib_parse.quote_plus(query)))
        data = data.split("list-group\">")[1].split("</ul>")[0]
        data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)
        patron = '<a href="(.*?)">(\\w*.*?)<'
        for channel in re.findall(patron, data, re.I):
            itemlist.append(Item(label=channel[1]+ " (acestreamsearch.net)",
                        action='play',
                        id=channel[0].replace("acestream://","")))
    except Exception as e:
        logger("search acestreamsearch.net: %s" % e, 'error')

    try:
        data = json.loads(http_get_text("https://search-ace.stream/search?query={}".format(urllib_parse.quote_plus(query))))
        for entry in data:
            itemlist.append(Item(label=entry["name"] + " (search-ace.stream)",
                        action='play',
                        id=entry["content_id"]))
    except Exception as e:
        logger("search search-ace.stream: %s" % e, 'error')

    # The engine goes last so the usual order does not change: deduplication keeps the
    # first appearance, so the two web sources still give exactly the same first results
    # as before.
    if get_setting("buscar_en_motor", True):
        try:
            from lib import catalog
            for canal in catalog.buscar(server, query):
                # The other two say which website they come from; this one points at the
                # addon's own Channels section, which is where it is also found.
                itemlist.append(Item(label=canal['nombre'] + " (canales)",
                                     action='play',
                                     infohash=canal['infohash'],
                                     icon=canal.get('logo') or '',
                                     motor=1))
        except Exception as e:
            logger("search motor: %s" % e, 'error')

    return itemlist


def search(url):
    itemlist = list()
    ids = list()

    try:
        if "://" not in url:
            itemlist = search_text(url)
        elif url.startswith("ass://"):
            global ass_ids
            ass_ids = list()
            itemlist = ass_decoder(url)
        else:
            data = http_get_text(url)

            if data:
                if "pastebin" in url or ".txt" in url:
                    data = data.replace("\n\n", "\n") #remove empty lines
                    data = data.replace("acestream://", "") #remove protocol
                    patron = "(?:.*?)======\n(.*)"
                    tmp = re.findall(patron, data, re.DOTALL) #remove text before "========"
                    if len(tmp) > 0:
                        data = tmp[0]
                    data = re.sub(r'(?m)^\===.*\n?', '', data) #remove lines starting with "==="
                    for it in re.findall(r'(.+?)\n([0-9a-f]{40})(?=\n|$)', data, re.DOTALL):
                        if len(it) == 2 and len(it[1]) > 0:
                                    name = it[0].replace("\n","")
                                    id = it[1]
                                    itemlist.append(Item(label=name ,action='play',id=id))
                elif "elcano" in url:
                    data = json.loads(data.split("linksData = ")[1].split(";")[0])
                    for link in data["links"]:
                        if len(link["url"]) >= 40:
                            itemlist.append(Item(label=link["name"] ,action='play',id=link["url"].replace("acestream://","")))
                elif "vercel.app" in url or "netlify.app" in url:
                    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)
                    data = data.replace("acestream://","")
                    patron = "<a href=[\'\"]([0-9a-f]{40})[\'\"](?:.*?)>(?: |)(\\w*.*?)(?: |)<"
                    for channel in re.findall(patron, data, re.I):
                        itemlist.append(Item(label=channel[1],
                                action='play',
                                id=channel[0]))
                else:
                    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;", "", data)

                    # 1) Structured list. parse_literal instead of eval(): before, any
                    #    remote list could run code on the machine.
                    entries = list()
                    encontrado = re.findall(r'(\[.*?])', data)
                    if encontrado:
                        aux = parse_literal(encontrado[0])
                        entries = aux if isinstance(aux, list) else list()

                    for n, it in enumerate(entries):
                        # A corrupt entry cannot bring the whole list down:
                        # that one is dropped and the rest keep being read.
                        try:
                            if not isinstance(it, dict):
                                continue

                            id = it.get("id") or it.get("url") or ''
                            id = re.findall('([0-9a-f]{40})', str(id), re.I)[0]

                            label = it.get("name") or it.get("title") or it.get("label")
                            icon = it.get("icon") or it.get("image") or it.get("thumb")

                            # n+1: the list is numbered from 1, like the other
                            # loop; before, this one started at "Opcion 0".
                            new_item = Item(label= label if label else translate(30030) % (n + 1, id), action='play', id=id)

                            if icon:
                                new_item.icon = icon

                            itemlist.append(new_item)
                        except Exception:
                            logger("search: entrada ignorada en %s: %s" % (url, it))

                    # 2) No usable structured list: m3u and, failing that, loose hashes.
                    if not itemlist:
                        for patron in [r'#EXTINF:-1.*?id="([^"]+)".*?([0-9a-f]{40})', '#EXTINF:-1.*?,(.*?)http.*?([0-9a-f]{40})']:
                            for label, id in re.findall(patron, data):
                                itemlist.append(Item(label=label, action='play', id=id))
                            if itemlist: break

                    if not itemlist:
                        for patron in [r"acestream://([0-9a-f]{40})", r'(?:"|>)([0-9a-f]{40})(?:"|<)']:
                            n = 1
                            for id in re.findall(patron, data, re.I):
                                if id not in ids:
                                    ids.append(id)
                                    itemlist.append(Item(label= translate(30030) % (n,id),
                                                         action='play',
                                                         id= id))
                                    n += 1
                            if itemlist: break

    except Exception as e:
        # This used to be 'except: pass': any network or format failure showed
        # up as "no links", with no trace in the log.
        logger("search '%s': %s" % (url, e), 'error')

    return itemlist


def kill_process():
    cmd_stop_acestream = get_setting("cmd_stop_acestream")

    if system_platform == 'windows':
        # subprocess instead of os.system: os.system opened a black console over Kodi.
        subprocess.call(['taskkill', '/F', '/IM', 'ace_engine.exe'], **no_window())

    elif cmd_stop_acestream:
        logger("cmd_stop_acestream= %s" % cmd_stop_acestream)
        subprocess.call(cmd_stop_acestream)


    time.sleep(0.75)

    # The engine version is cached and has to be forgotten to know if it is still alive.
    # And the detected engine with it, or after starting the other we would name this one.
    server.invalidate()
    forget_engine()

    if not server.available:
        logger("Motor Acestream cerrado")
        xbmcgui.Dialog().notification(HEADING, translate(30035),
                                      os.path.join(runtime_path, 'resources', 'media', 'icono_aces_horus.png'))
        return True
    else:
        logger("Motor Acestream NO cerrado")
        xbmcgui.Dialog().notification(HEADING, translate(30040),
                                      os.path.join(runtime_path, 'resources', 'media', 'error.png'))
        return False


_qr_base = None


def qr_base():
    """(url template, file suffix) per the chosen QR format.

    It is worked out once per invocation: painting a list of 300 channels calls
    qr_poster() 300 times, and rereading the setting and asking for the IP on every row is
    exactly what was taken out of this loop back in the day.

    With the http format any phone with VLC opens the QR, with no need to have AceStream
    installed, which is the scenario the guide recommends for diagnosis. The host comes
    from server and not from the setting: rereading it gave addresses different from the
    ones the rest of the addon uses."""
    global _qr_base

    if _qr_base is not None:
        return _qr_base

    _qr_base = ('acestream://%s', '')

    if get_setting('qr_formato'):
        host = server.host

        # A QR with 127.0.0.1 inside is no use to anybody scanning it with a phone.
        if host in HOSTS_LOCALES:
            host = xbmc.getIPAddress() or ''

        if host and host not in HOSTS_LOCALES:
            # The suffix carries the host because the PNG is cached: without it, changing
            # format or engine would keep serving the previous file forever.
            _qr_base = (f'http://{host}:{server.port}/ace/getstream?id=%s',
                        'h%s_' % host.replace('.', ''))
        else:
            logger('qr_poster: sin direccion util para el QR http, se usa acestream://')

    return _qr_base


def qr_poster(id):
    """Generates (only once) the QR PNG of an acestream:// link.

    It used to be regenerated on every painting of the directory: on a list of 300
    channels that was 300 disk writes every time it was browsed."""
    from lib import qr

    plantilla, sufijo = qr_base()
    poster_url = os.path.join(translatePath('special://temp'),
                              'ekhorus_qr_%s%s.png' % (sufijo, id))

    return qr.generar(plantilla % id, poster_url)


def run(item):
    itemlist = list()

    if not item.action:
        logger("Item sin acción")
        return

    logger("Ejecutando " + str(item))
    if item.action == "mainmenu":
        # The setting is looked at here and not inside the module so as not to import it
        # on every opening of the menu: the wizard drags in lib/netscan.py and the engine
        # client, and all of that is needed once in the addon's life.
        #
        # And only with a directory of our own: from llamada_externa() this would hijack
        # the playback another addon has just asked for.
        if plugin_handle() >= 0 and not get_setting('asistente_hecho', False):
            from lib import setup_wizard
            setup_wizard.mostrar()

        itemlist = mainmenu()

    elif item.action == "experimental":
        itemlist = experimental_menu()

    elif item.action == "aviso_version":
        xbmcgui.Dialog().ok(HEADING, translate(30132))

    elif item.action == "kill":
        if kill_process():
            xbmc.executebuiltin('Container.Refresh')

    elif item.action == "historial":
        for it in get_historial():
            itemlist.append(Item(label= it.get('title'),
                                 action='play',
                                 infohash=it.get('infohash'),
                                 icon=it.get('icon'),
                                 plot=it.get('plot'),
                                 hist=1,
                                 ctx_del=it.get('infohash')))

    elif item.action == "del_historial":
        if item.infohash:
            del_historial(item.infohash)
        elif xbmcgui.Dialog().yesno(HEADING, translate(30051)):
            # Emptying the whole history has no way back, so it is confirmed.
            del_historial()
        else:
            return

        xbmc.executebuiltin('Container.Refresh')
        return

    elif item.action == "search":
        # With no earlier search the box opens empty. It used to come preloaded with
        # acetv.org, a domain that no longer exists: the user pressed accept and got
        # a network error on their first search.
        url_list = xbmcgui.Dialog().input(translate(30032), get_setting("last_search", ""))
        if url_list:
            itemlist = list()
            tmp_itemlist = list()
            ids = set()
            for url in url_list.split(";"):
                if url:
                    tmp_itemlist.append(Item(label=">>>>>>>>>> Source [{}] <<<<<<<<<<".format(url) ,action='',id=url))
                    tmp_itemlist = tmp_itemlist + search(url)
            for found in tmp_itemlist:
                # An item with no 'id' is no good as a key: Item returns '' for whatever it
                # does not have, so everything arriving by infohash would share the same
                # one and merge into one. Today everything carries an id and the result is
                # identical.
                clave = found.id or found.infohash or found.url
                if clave not in ids:
                    itemlist.append(found)
                    ids.add(clave)
            # There are results if some item is playable (separators do not count;
            # the earlier threshold by lengths failed with a trailing ';').
            if any(it.action == 'play' for it in itemlist):
                set_setting("last_search", url_list)
            else:
                xbmcgui.Dialog().ok(HEADING,  translate(30031) % url_list)
                itemlist = list()

        if not itemlist:
            # Cancelled or with no results: the directory was left half open
            # (before it even painted a list of separators only).
            cerrar_directorio(succeeded=False)
            return

    elif item.action == 'open_settings':
        clasica_antes = ui_common.clasica()
        xbmcaddon.Addon().openSettings()
        # Each row of the painted menu records whether it is a folder, and that depends on
        # the mode. Changing it without repainting left EspaKodi Addons and the APKs dead.
        if ui_common.clasica() != clasica_antes:
            xbmc.executebuiltin('Container.Refresh')

    elif item.action == 'cuadro_mandos':
        # The directory is closed BEFORE opening the window: while the plugin is still
        # resolving, Kodi brings up its waiting dialog and would compete for the focus.
        cerrar_directorio(succeeded=False)

        if ui_common.clasica():
            xbmcaddon.Addon().openSettings()
            return

        from lib import control_panel
        control_panel.mostrar()
        return

    elif item.action == 'web':
        cerrar_directorio(succeeded=False)

        from lib import web_ui
        web_ui.mostrar()
        return

    elif item.action == 'guia':
        cerrar_directorio(succeeded=False)

        from lib import guide_ui
        guide_ui.mostrar()
        return

    elif item.action == 'universo':
        cerrar_directorio(succeeded=False)

        # What the dot on the menu announces is that there is something here to see,
        # and by now it has been seen.
        set_setting('universo_visto', True)

        from lib import universe_ui
        universe_ui.mostrar()
        return

    elif item.action == 'apk_menu':
        if not (ui_common.clasica() or item.clasico):
            cerrar_directorio(succeeded=False)
            if not apk_ventana():
                volver_a_lo_clasico('apk_menu')
            return

        if plugin_handle() < 0:
            entrar_en_lista('apk_menu')
            return

        itemlist = apk_menu()

    elif item.action == 'catalogo':
        from lib import channels_ui

        # The window of our own only opens from the root. Inside it the levels do not
        # relaunch the addon, so an item that already carries a mode comes from the
        # classic route.
        if not (ui_common.clasica() or item.clasico or item.modo):
            cerrar_directorio(succeeded=False)
            if not channels_ui.mostrar_explorador():
                volver_a_lo_clasico('catalogo')
            return

        if plugin_handle() < 0:
            entrar_en_lista('catalogo')
            return

        itemlist = channels_ui.filas_clasicas(item)

    elif item.action == 'catalogo_refresh':
        from lib import channels_ui
        if channels_ui.actualizar():
            xbmc.executebuiltin('Container.Refresh')
        return

    elif item.action == 'download_apk':
        download_apk(item.filename, item.apk_url, item.sha256)

    elif item.action == 'apk_info':
        xbmcgui.Dialog().ok(HEADING, translate(30075))

    elif item.action == 'espakodi_addons':
        # The import goes in here on purpose: if you do not enter the menu, it is not loaded
        from lib import espakodi_installer

        if not (ui_common.clasica() or item.clasico):
            cerrar_directorio(succeeded=False)
            if not espakodi_installer.mostrar_ventana():
                volver_a_lo_clasico('espakodi_addons')
            return

        handle = plugin_handle()
        if handle < 0:
            entrar_en_lista('espakodi_addons')
            return

        espakodi_installer.render_menu(handle)
        # render_menu() paints the items but does not close: the closing always goes through
        # here, which is what avoids the second endOfDirectory() in the __main__ finally
        cerrar_directorio(succeeded=True, cache=True)
        return

    elif item.action == 'ek_launch':
        from lib import espakodi_installer
        espakodi_installer.launch_by_id(item.addon_id)

    elif item.action == 'ek_open_web':
        from lib import espakodi_installer
        espakodi_installer.open_web()

    elif item.action == 'ek_open_repo':
        from lib import espakodi_installer
        espakodi_installer.open_repo_unificado()

    elif item.action == 'ek_open_apk':
        from lib import espakodi_installer
        espakodi_installer.open_apk_latest()

    elif item.action == 'play':
        id = url = infohash = None

        # Only the items that ALREADY carry a link (history, lists) bring their own
        # metadata. The "Reproducir ID" menu item does not: its label is the menu
        # text and must not end up as the video title.
        meta = {'title': '', 'iconimage': '', 'plot': '', 'desde_motor': False}

        if item.id or item.url or item.infohash:
            meta = {'title': item.label or item.title or '',
                    'iconimage': item.icon or '',
                    'plot': item.plot or '',
                    'desde_motor': bool(item.motor)}

        if item.id:
            id =item.id
        elif item.url:
            url=item.url
        elif item.infohash:
            infohash=item.infohash
        else:
            last_id = get_setting("last_id", "a0270364634d9c49279ba61ae3d8467809fb7095")
            input = xbmcgui.Dialog().input(translate(30022), last_id if get_setting("remerber_last_id") else "")
            if re.findall('^(http|magnet)', input, re.I):
                url = input
            elif re.findall('([0-9a-f]{40})', input, re.I):
                id = re.findall('([0-9a-f]{40})', input, re.I)[0]
            elif input:
                xbmcgui.Dialog().ok(HEADING, translate(30031) % input)
                return

        if id:
            acestreams(id=id, **meta)
        elif url and url.lower().endswith('.torrent'):
            infohash = read_torrent(url)
            if infohash:
                acestreams(infohash=infohash, **meta)
        elif url and url.lower().startswith('magnet:'):
            infohash = re.findall('xt=urn:btih:([a-f0-9]+)', url, re.I)
            if infohash:
                acestreams(infohash=infohash[0], **meta)
        elif url:
            acestreams(url=url, **meta)
        elif infohash:
            acestreams(infohash=infohash, **meta)

        #xbmc.executebuiltin('Container.Refresh')

    if not itemlist:
        # An empty folder (e.g. the history just emptied, which is repainted
        # with Container.Refresh) has to be closed all the same: without this Kodi
        # was left showing the old list, already deleted.
        if item.action in ("mainmenu", "historial"):
            cerrar_directorio(succeeded=True)
        return

    handle = plugin_handle()
    if handle < 0:
        return

    # They are read once, not once per channel.
    icon_default = os.path.join(runtime_path, 'icon.png')
    show_qr = get_setting("show_qr_codes")
    vaciar_url = 'RunPlugin(%s?%s)' % (sys.argv[0], Item(action='del_historial').tourl())

    for entrada in itemlist:
        listitem = xbmcgui.ListItem(entrada.label or entrada.title)
        infotag = listitem.getVideoInfoTag()
        infotag.setTitle(entrada.label or entrada.title)
        infotag.setMediaType('video')
        infotag.setPlot(entrada.plot or entrada.id or entrada.url)

        poster_url = entrada.icon or icon_default
        # Only real ids (a 40-char hash) carry a QR: the source separators and the
        # search texts are not acestream links.
        if show_qr and entrada.id and re.match(r'[0-9a-f]{40}\Z', str(entrada.id), re.I):
            poster_url = qr_poster(entrada.id) or poster_url

        listitem.setArt({'icon': entrada.icon or icon_default, 'poster': poster_url})

        if entrada.hist:
            # "Vaciar" goes on ALL the history rows. If it only hung from the ones
            # that have an infohash, a row without it would leave the user with no
            # way of emptying it from the interface.
            ctx = list()
            if entrada.ctx_del:
                ctx.append((translate(30048), 'RunPlugin(%s?%s)' % (sys.argv[0], Item(action='del_historial', infohash=entrada.ctx_del).tourl())))
            ctx.append((translate(30049), vaciar_url))
            listitem.addContextMenuItems(ctx)

        if entrada.isPlayable:
            listitem.setProperty('IsPlayable', 'true')
            isFolder = False

        elif isinstance(entrada.isFolder, bool):
            isFolder = entrada.isFolder

        elif entrada.action in ["", "kill", "play", "open_settings", "cuadro_mandos",
                               "guia", "universo", "catalogo_refresh", "web",
                               "aviso_version"]:
            isFolder = False

        else:
            isFolder = True

        xbmcplugin.addDirectoryItem(
            handle=handle,
            url='%s?%s' % (sys.argv[0], entrada.tourl()),
            listitem=listitem,
            isFolder= isFolder,
            totalItems=len(itemlist)
        )

    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_NONE)
    cerrar_directorio(succeeded=True, cache=True)


def llamada_externa(argumentos):
    """Another addon asks us to play something (StreamNinja and company)."""
    logger("Llamada externa: %s" % argumentos)
    action = argumentos.get('action', '').lower()

    if action == 'install_acestream':
        if system_platform in ['linux', 'windows']:
            install_acestream()
        return

    if action != 'play' or not (argumentos.get('id') or argumentos.get('url') or argumentos.get('infohash')):
        return

    # StreamNinja bounces back to Horus when its native engine does not play; without
    # this circuit breaker the forwarding enters an infinite Horus<->StreamNinja loop.
    snb_key = 'ekhorus_snb_' + (argumentos.get('id') or argumentos.get('infohash') or argumentos.get('url') or '')
    win = xbmcgui.Window(10000)
    prev = win.getProperty(snb_key)
    bounced = False
    if prev:
        try:
            bounced = (time.time() - float(prev)) < 15
        except ValueError:
            pass

    if get_setting("redirect_streamninja") and xbmc.getCondVisibility('System.HasAddon(plugin.video.streamninja)') and not bounced:
        win.setProperty(snb_key, str(time.time()))
        fwd = {k: v for k, v in argumentos.items() if k != 'action' and v}
        xbmc.executebuiltin('RunPlugin(plugin://plugin.video.streamninja/?action=acestream&%s)' % urllib_parse.urlencode(fwd))
        return

    win.clearProperty(snb_key)
    url = argumentos.get('url') or ''

    if url.lower().endswith('.torrent'):
        infohash = read_torrent(url, argumentos.get('headers'))
        if not infohash:
            # This used to be a mute exit(0): no warning, no log, nothing.
            notification_error(translate(30031) % url)
            return
        argumentos['infohash'] = infohash
        argumentos['url'] = None

    elif url.lower().startswith('magnet:'):
        infohash = re.findall('xt=urn:btih:([a-f0-9]+)', url, re.I)
        if not infohash:
            notification_error(translate(30031) % url)
            return
        argumentos['infohash'] = infohash[0]
        argumentos['url'] = None

    acestreams(id=argumentos.get('id'),
               url=argumentos.get('url'),
               infohash=argumentos.get('infohash'),
               title=argumentos.get('title'),
               iconimage=argumentos.get('iconimage'),
               plot=argumentos.get('plot'))


if __name__ == '__main__':
    try:
        if system_platform in ['linux', 'windows'] and not get_setting("install_acestream"):
            install_acestream()

        item = None

        # len(): invoked via RunScript (with no plugin arguments) this blew up
        # with IndexError before getting anywhere.
        if len(sys.argv) > 2 and sys.argv[2]:
            try:
                item = Item().fromurl(sys.argv[2])
            except Exception:
                # It is not an item of ours: it is another addon's query.
                argumentos = dict()
                for c in sys.argv[2][1:].split('&'):
                    if '=' not in c:
                        continue
                    # split('=', 1): a value with '=' inside (base64, signed urls)
                    # broke the unpacking and brought the external call down.
                    k, v = c.split('=', 1)
                    argumentos[k] = urllib_parse.unquote_plus(ensure_str(v))

                llamada_externa(argumentos)
        else:
            item = Item(action='mainmenu')

        if item:
            run(item)

    finally:
        # Safety net. Other addons invoke us with PlayMedia, and there Kodi gives
        # us a handle and waits for an answer: if the script ends without giving
        # one (an early exit, an unknown action, an error), Kodi throws a phantom
        # "playback failed". cerrar_directorio() does nothing if there is no
        # handle or if some branch has already closed it.
        cerrar_directorio(succeeded=False)

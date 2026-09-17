# -*- coding: utf-8 -*-

# NOTE: sys and xbmcplugin look unused here and a linter will flag them as such,
# but default.py does 'from lib.utils import *' and receives them this way. If they
# are removed, the addon stops starting.
import sys, os ,re
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import ast
import base64
import json
import subprocess
import time
import urllib.parse as urllib_parse
import urllib.request as urllib_request

from threading import Lock

LOGINFO = xbmc.LOGINFO

try:
    translatePath = xbmcvfs.translatePath
except:
    translatePath = xbmc.translatePath

ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
HEADING = "%s (%s)" %(ADDON_NAME,ADDON_VERSION)

runtime_path = translatePath(ADDON.getAddonInfo('Path'))
icon_path = os.path.join(runtime_path, 'icon.png')
data_path = translatePath(ADDON.getAddonInfo('Profile'))
translate = ADDON.getLocalizedString

# No network request may be left hanging: Kodi freezes along with it.
HTTP_TIMEOUT = 10
# Download cap. Playlists and .torrent files are a few KB; anything this size is
# an error or an abuse, and reading it whole would exhaust memory.
HTTP_MAX_BYTES = 16 * 1024 * 1024
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'


def ensure_str(value, encoding='utf-8', errors='replace'):
    if isinstance(value, bytes):
        return value.decode(encoding, errors)
    return str(value)


def ensure_binary(value, encoding='utf-8'):
    if isinstance(value, str):
        return value.encode(encoding)
    return value


def parse_literal(value):
    """Turns a text into a Python object without using eval().

    Accepts JSON and Python literals (lists, dicts, numbers, strings).
    Returns None if the text is not a valid literal."""
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except Exception:
        pass

    try:
        return ast.literal_eval(value)
    except Exception:
        return None


def parse_headers(headers):
    if not headers:
        return dict()
    if isinstance(headers, dict):
        return headers

    value = parse_literal(headers)
    return value if isinstance(value, dict) else dict()


def http_get_bytes(url, headers=None, timeout=HTTP_TIMEOUT, max_bytes=HTTP_MAX_BYTES):
    headers = dict(parse_headers(headers))
    headers.setdefault('User-Agent', USER_AGENT)

    req = urllib_request.Request(url, data=None, headers=headers)

    with urllib_request.urlopen(req, timeout=timeout) as response:
        # One byte more is read, to tell "exactly at the limit" from "over it".
        # With no cap, a url returning gigabytes would exhaust Kodi's memory.
        data = response.read(max_bytes + 1)

    if len(data) > max_bytes:
        raise ValueError("respuesta demasiado grande (mas de %s bytes): %s" % (max_bytes, url))

    return data


def http_get_text(url, headers=None, timeout=HTTP_TIMEOUT):
    return ensure_str(http_get_bytes(url, headers, timeout))


class Item(object):
    defaults = {}

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __contains__(self, item):
        return item in self.__dict__

    def __getattribute__(self, item):
        return object.__getattribute__(self, item)

    def __getattr__(self, item):
        if item.startswith("__"):
            return object.__getattribute__(self, item)
        else:
            return self.defaults.get(item, '')

    def __str__(self):
        return '{%s}' % (', '.join(['\'%s\': %s' % (k, repr(self.__dict__[k])) for k in sorted(self.__dict__.keys())]))

    def tourl(self):
        value = ensure_binary(self.__str__())
        return ensure_str(urllib_parse.quote(base64.b64encode(value)))

    def fromurl(self, url):
        str_item = ensure_str(base64.b64decode(urllib_parse.unquote(url)))
        item = ast.literal_eval(str_item)
        if not isinstance(item, dict):
            raise ValueError("item no valido: %s" % str_item)
        self.__dict__.update(item)
        return self


def logger(message, level=None):
    def format_message(data=""):
        try:
            value = str(data)
        except Exception:
            value = repr(data)

        return ensure_str(value)

    texto = '[%s] %s' % (ADDON.getAddonInfo('id'), format_message(message))

    try:
        if level == 'error':
            xbmc.log("######## ERROR #########", xbmc.LOGERROR)
            xbmc.log(texto, xbmc.LOGERROR)
        else:
            xbmc.log(texto, LOGINFO)
    except:
        xbmc.log(str([texto]), LOGINFO)


locker = Lock()
def load_json_file(path):
    with locker:
        data = open(path, 'rb').read()

    data = load_json(ensure_str(data))
    return data


def dump_json_file(data, path, compacto=False):
    """Writes json atomically.

    With compacto, no indentation and no sorted keys. The engine's catalogue is 1800
    channels and in the readable format it goes from 300 KB to over a megabyte, which on a
    TV box shows both when writing and when reading."""
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    if compacto:
        texto = dump_json(data, ensure_ascii=False, separators=(',', ':'))
    else:
        texto = dump_json(data)

    # dump_json() returns '' when it cannot serialise. Writing that would erase
    # the previous content; better to fail and leave the file as it was.
    if not texto:
        raise ValueError("contenido no serializable; no se sobrescribe %s" % path)

    # Atomic write: if Kodi closes halfway through writing, the original file
    # stays intact instead of being left truncated.
    tmp_path = '%s.%s.tmp' % (path, os.getpid())
    with locker:
        try:
            with open(tmp_path, 'wb') as f:
                f.write(ensure_binary(texto))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except OSError: pass
            raise


def load_json(*args, **kwargs):
    if "object_hook" not in kwargs:
        kwargs["object_hook"] = set_encoding

    try:
        value = json.loads(*args, **kwargs)
    except Exception:
        value = {}

    return value


def dump_json(*args, **kwargs):
    if not kwargs:
        kwargs = {
            'indent': 4,
            'skipkeys': True,
            'sort_keys': True,
            'ensure_ascii': False
        }

    try:
        value = json.dumps(*args, **kwargs)
    except Exception:
        value = ''

    return value


def set_encoding(dct):
    if isinstance(dct, dict):
        return dict((set_encoding(key), set_encoding(value)) for key, value in dct.items())
    elif isinstance(dct, list):
        return [set_encoding(element) for element in dct]
    elif isinstance(dct, (str, bytes)):
        return ensure_str(dct)
    else:
        return dct


def get_setting(name, default=None):
    value = ADDON.getSetting(name)

    if not value:
        return default
    elif value == 'true':
        return True
    elif value == 'false':
        return False

    try:
        return int(value)
    except ValueError:
        pass

    parsed = parse_literal(value)
    if isinstance(parsed, (list, dict)):
        return parsed

    return value


def set_setting(name, value):
    try:
        if isinstance(value, bool):
            value = "true" if value else "false"
        elif isinstance(value, (int, list)):
            value = str(value)
        elif not isinstance(value, str):
            value = dump_json(value)

        ADDON.setSetting(name, value)

    except Exception as ex:
        logger("Error al convertir '%s' no se guarda el valor \n%s" % (name, ex), 'error')
        return None

    return value


# Ace engines the addon knows how to launch. The first one is only the dropdown label;
# the AceServe one is also used as the package name when firing the Android intent.
ENGINE_ACESTREAM = "org.acestream.----"
ENGINE_ACESERVE = "org.free.aceserve"


def active_engine():
    """Engine chosen in the settings. Outside Android only AceStream exists."""
    if system_platform != 'android':
        return ENGINE_ACESTREAM

    return get_setting("ace_engine") or ENGINE_ACESTREAM


def engine_port(engine=None):
    """Port of the given engine, or of the active one if none is given.

    AceServe pins 6878 and does not let it be changed without root, so whoever moves
    it by editing their acestream.conf needs a separate setting. Empty means "the same
    as AceStream", so that whoever had already moved it with the only port there used
    to be is not left unable to play after updating."""
    if (engine or active_engine()) == ENGINE_ACESERVE:
        return get_setting("aceserve_port") or get_setting("ace_port", 6878)

    return get_setting("ace_port", 6878)


def engine_name(engine):
    """Presentable name of the engine, for messages to the user."""
    return 'AceServe' if engine == ENGINE_ACESERVE else 'AceStream'


_ENGINE_PROP = 'ekhorus_engine_'
# Addresses where the engine runs on this very device.
HOSTS_LOCALES = ('127.0.0.1', 'localhost', '::1')


def forget_engine(servidor=None):
    """Forgets the detected engine. Mandatory after stopping or starting one."""
    xbmcgui.Window(10000).clearProperty(_ENGINE_PROP + (servidor or server).base)


def detect_engine(servidor=None):
    """Which engine is really answering, or None if there is no way to know.

    The only reliable signal is /pl.m3u, which AceServe serves and the AceStream engine
    does not. Guessing by version number is no good: measured in September 2026, AceStream
    is on 3.2.22 and AceServe on 3.2.14, so neither the threshold nor the order that were
    assumed hold up."""
    servidor = servidor or server

    version = servidor.version
    if not version:
        return None

    # There used to be a shortcut here: on desktop with a local engine, take it for
    # granted that it is AceStream and save the request. The assumption is false, because
    # AceServe is also shipped as a Docker container and may be running on the same
    # machine as Kodi. Assuming is what the previous version got wrong, so it always asks.
    # It comes cheap: the verdict stays cached for the whole Kodi session.
    window = xbmcgui.Window(10000)
    clave = _ENGINE_PROP + servidor.base

    # The verdict is stored next to the version that was answering back then. If that
    # version changes there is another engine on the other side, and the earlier verdict
    # no longer holds. On Android the other engine cannot be stopped from here, so without
    # this check a stale verdict lasted the whole Kodi session.
    guardado = window.getProperty(clave)
    if guardado.startswith(version + '|'):
        return guardado.split('|', 1)[1]

    sirve = servidor.playlist_status()

    # With no clear answer nothing is decided and nothing is cached. The verdict lasts the
    # whole Kodi session, so an unlucky probe while the engine is broadcasting would leave
    # the engine misidentified until a restart. Returning what the user has chosen also
    # keeps check_engine()'s warning quiet, which is right when we do not know.
    if sirve is None:
        logger('detect_engine: /pl.m3u sin respuesta, no se decide ni se cachea')
        return active_engine()

    detectado = ENGINE_ACESERVE if sirve else ENGINE_ACESTREAM

    window.setProperty(clave, version + '|' + detectado)
    return detectado


def get_system_platform():
    plataforma = arquitectura = linux_id = "unknown"
    root = True

    if 'ANDROID_STORAGE' in os.environ:
        plataforma = "android"

    elif xbmc.getCondVisibility('system.platform.linux.raspberrypi') or xbmc.getCondVisibility('system.platform.linux'):
        plataforma = "linux"
        if "arm" in os.uname()[4]:
            arquitectura = "arm"
        elif "aarch" in os.uname()[4]:
            arquitectura = "aarch"
        elif "x86" in os.uname()[4]:
            arquitectura = "x86"

        try:
            with open("/etc/os-release", 'rb') as f:
                data = ensure_str(f.read())
                linux_id = re.findall(r"""\bid\s?=\s?["']?(\w+)""", data, re.I)[0]
                set_setting("linux_id", linux_id)
        except:pass

        if os.geteuid() == 0:
            root = True
        else:
            root = False
            if arquitectura == "arm":
                if linux_id not in ['osmc','openelec','raspbian','raspios']:
                    plataforma = str(os.uname())
            elif arquitectura != "x86":
                plataforma = str(os.uname())

    elif xbmc.getCondVisibility('system.platform.windows'):
        plataforma = "windows"

    elif xbmc.getCondVisibility('system.platform.tvos'):  # Supported only on Kodi 19.x
        plataforma = "android" #"tvos"

    return (plataforma, arquitectura, root)


def no_window():
    """Stops taskkill/subprocess from opening a black console on top of Kodi."""
    kwargs = {'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}

    if hasattr(subprocess, 'STARTUPINFO'):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'] = startupinfo
        kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    return kwargs


class DownloadCanceled(Exception):
    pass


# Android folders where a file manager can read the APK
APK_FOLDER_CANDIDATES = (
    '/storage/emulated/0/Download/',
    '/storage/self/primary/Download/',
    '/sdcard/Download/',
)

APK_DOWNLOAD_TIMEOUT = 30
APK_CHUNK_SIZE = 128 * 1024
PM_INSTALL_TIMEOUT = 180


def translate_fmt(string_id, *args):
    # If the string is not loaded, translate() returns ''. That happens when you edit
    # strings.po and do not restart Kodi, or with an incomplete language. Formatting ''
    # with arguments raises TypeError, so it is better to show the bare data than to
    # blow up
    text = translate(string_id) or ''

    if not args:
        return text

    try:
        return text % args
    except TypeError:
        logger("Cadena %s sin cargar o con placeholders erroneos" % string_id, 'error')
        return '\n'.join([text] + [str(a) for a in args]).strip()


def format_size(size):
    size = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return "%.1f %s" % (size, unit)
        size /= 1024.0
    return "%.1f TB" % size


def join_path(folder, filename):
    # On Windows os.path.join inserts '\' and breaks VFS paths like smb://
    if "://" in folder:
        return folder.rstrip('/') + '/' + filename
    return os.path.join(folder, filename)


def apk_looks_valid(path):
    # An APK is still a ZIP. If it is cut short it is missing the index at the end and it
    # shows without touching the network. It catches what the size does not, like servers
    # that do not send Content-Length or half-finished files from old versions.
    # Returns True or False, and None when there is no way to know, as in smb://
    if "://" in path:
        return None

    try:
        import zipfile
        return zipfile.is_zipfile(path)
    except Exception as ex:
        logger("No se pudo validar el APK %s: %s" % (path, ex))
        return None


def default_apk_folder():
    last = get_setting("last_apk_folder", "")
    if isinstance(last, str) and last and xbmcvfs.exists(last):
        return last

    if system_platform == 'android':
        for folder in APK_FOLDER_CANDIDATES:
            if xbmcvfs.exists(folder):
                return folder

    return ""


def download_to(url, dest, dp=None, message=""):
    request = urllib_request.Request(url, headers={'User-Agent': USER_AGENT})
    response = urllib_request.urlopen(request, timeout=APK_DOWNLOAD_TIMEOUT)
    downloaded = 0

    try:
        total = response.headers.get('Content-Length')
        total = int(total) if total and total.isdigit() else 0

        handle = xbmcvfs.File(dest, 'w')
        try:
            while True:
                if dp and dp.iscanceled():
                    raise DownloadCanceled()

                chunk = response.read(APK_CHUNK_SIZE)
                if not chunk:
                    break

                # write() does not raise, it returns False. If you do not look at it, a full
                # disk gives you a "correct" download with a cut APK inside
                if not handle.write(bytearray(chunk)):
                    raise IOError(translate(30072) or "Error al escribir en el disco")

                downloaded += len(chunk)

                if dp:
                    if total:
                        dp.update(min(int(downloaded * 100 / total), 100),
                                  "%s\n%s / %s" % (message, format_size(downloaded), format_size(total)))
                    else:
                        dp.update(0, "%s\n%s" % (message, format_size(downloaded)))
        finally:
            handle.close()
    finally:
        response.close()

    # downloaded is the bytes that arrived from the network, not the ones written.
    # Before calling this good, the real size of the file has to be checked
    written = xbmcvfs.Stat(dest).st_size()
    if total and written < total:
        raise IOError("Descarga incompleta (%s de %s)" % (format_size(written), format_size(total)))

    return written


def kodi_major_version():
    try:
        return int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
    except Exception:
        return 0


def is_espakodi_build():
    """Whether we are inside the EspaKodi APK, which brings its own install bridge.

    It is recognised by the addon path: on Android it always hangs off the data
    folder of the application hosting Kodi."""
    return 'espakodi.kodi' in runtime_path


def apk_autoinstall_supported():
    # With the EspaKodi bridge the Kodi version does not matter, because the conversion
    # from file:// to content:// is done by the APK itself with its FileProvider. Without
    # a bridge Kodi 22 is needed: from 21 down the intent installs nothing and can even
    # close Kodi, so it is not even attempted and manual instructions are used
    if system_platform != 'android':
        return False

    return is_espakodi_build() or kodi_major_version() >= 22


# This class name is generated by the obfuscator when AceServe is compiled, so it can
# change in any version of theirs and there is no way to detect it from Kodi.
ACESERVE_LINK_ACTIVITY = 'crc644baf9324e22bb51e.LinkHandlerActivity'


def android_engine_launch(engine=None):
    """Builtin that opens the app of the given engine on Android, or of the active one."""
    if (engine or active_engine()) != ENGINE_ACESERVE:
        return 'StartAndroidActivity("","org.acestream.action.start_content","","acestream:?content_id=launch")'

    # The last five arguments of StartAndroidActivity are Kodi 20 onwards. On Kodi 19 the
    # class name is ignored, so there the VIEW intent is sent plain, which AceServe has
    # handled since its 1.3.5.
    if kodi_major_version() >= 20:
        return (f'StartAndroidActivity("{ENGINE_ACESERVE}","","","acestream://",'
                f'"","","","","{ACESERVE_LINK_ACTIVITY}")')

    return f'StartAndroidActivity("{ENGINE_ACESERVE}","android.intent.action.VIEW","","acestream://")'


# How long an open-window mark stays valid. It only matters in the rare case where
# the previous window no longer exists: while it is open the user cannot press the
# menu row again.
_PESTILLO_VALIDEZ_S = 60


def hay_pestillo(clave):
    """True if somebody holds that mark and it has not gone stale.

    Only for looking. Whoever wants to take it calls echar_pestillo(), which is the one
    that decides and marks in one go."""
    marca = xbmcgui.Window(10000).getProperty(clave)

    if not marca:
        return False

    try:
        return (time.time() - float(marca)) < _PESTILLO_VALIDEZ_S
    except ValueError:
        # Something that is not a time is not a mark anybody can trust.
        return False


def echar_pestillo(clave):
    """Marks that a modal window of the addon just opened; False if one was already open.

    Every press of the menu launches the addon from scratch, so a double click would open
    two identical overlapping windows, and closing the top one would look as if it did
    not close. The mark lives in the Home window because a module variable is not shared
    between invocations, and it stores the time and not a plain '1': if Kodi decides to
    kill the script between setting it and clearing it, an eternal latch would leave the
    menu entry dead for the rest of the session, and silently."""
    if hay_pestillo(clave):
        return False

    xbmcgui.Window(10000).setProperty(clave, str(time.time()))
    return True


def refrescar_pestillo(clave):
    """Renews the mark of a job that is still alive.

    The latch expires after 60 s so that a dead script does not leave the menu entry
    blocked. A genuinely long job, such as downloading ten catalogue pages against a slow
    remote engine, can go past that and let a second one start. Whoever takes a while
    calls this between steps."""
    xbmcgui.Window(10000).setProperty(clave, str(time.time()))


def quitar_pestillo(clave):
    xbmcgui.Window(10000).clearProperty(clave)


def folder_is_writable(folder):
    # Better to find out now than after swallowing 100 MB
    probe = join_path(folder, '.ekhorus_write_test')
    written = False
    try:
        handle = xbmcvfs.File(probe, 'w')
        try:
            written = bool(handle.write(bytearray(b'0')))
        finally:
            handle.close()
    except Exception as ex:
        logger("Carpeta no escribible (%s): %s" % (folder, ex))
        written = False

    xbmcvfs.delete(probe)
    return written


def copy_with_progress(source_path, target_path, message):
    # xbmcvfs.copy() leaves Kodi frozen, with no bar and no way to cancel. With a 100 MB
    # APK that is no good, so it is copied in chunks the same as when downloading
    dp = xbmcgui.DialogProgress()
    dp.create(HEADING, message)

    try:
        source = xbmcvfs.File(source_path)
        try:
            total = source.size()
            target = xbmcvfs.File(target_path, 'w')
            try:
                copied = 0
                while True:
                    if dp.iscanceled():
                        raise DownloadCanceled()

                    chunk = source.readBytes(APK_CHUNK_SIZE)
                    if not chunk:
                        break

                    if not target.write(chunk):
                        raise IOError(translate(30072) or "Error al escribir en el disco")

                    copied += len(chunk)

                    if total:
                        dp.update(min(int(copied * 100 / total), 100),
                                  "%s\n%s / %s" % (message, format_size(copied), format_size(total)))
            finally:
                target.close()
        finally:
            source.close()
    finally:
        dp.close()

    written = xbmcvfs.Stat(target_path).st_size()
    if total and written < total:
        raise IOError("Copia incompleta (%s de %s)" % (format_size(written), format_size(total)))

    return written


def stage_apk_public(path):
    # The Android installer does not see Kodi's private sandbox. For the intent to work,
    # the APK has to be in public storage, that is to say in /storage/
    if path.startswith('/storage/'):
        return path

    target_dir = next((f for f in APK_FOLDER_CANDIDATES if xbmcvfs.exists(f)), None)
    if not target_dir:
        logger("Sin almacenamiento publico donde preparar el APK", 'error')
        return None

    target = join_path(target_dir, os.path.basename(path))
    if xbmcvfs.exists(target):
        xbmcvfs.delete(target)

    try:
        copy_with_progress(path, target, translate(30066))
    except DownloadCanceled:
        xbmcvfs.delete(target)
        logger("Preparacion del APK cancelada por el usuario")
        return None
    except Exception as ex:
        xbmcvfs.delete(target)
        logger("No se pudo copiar el APK a almacenamiento publico: %s" % ex, 'error')
        xbmcgui.Dialog().ok(HEADING, translate_fmt(30073, os.path.basename(path), ex))
        return None

    logger("APK preparado en almacenamiento publico: %s" % target)
    return target


def try_pm_install(apk_path):
    # Only works with root or with Kodi as a system app, which some Android TV boxes do
    attempts = (
        ['pm', 'install', '-r', apk_path],
        ['su', '-c', 'pm install -r "%s"' % apk_path],
    )

    for command in attempts:
        try:
            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=PM_INSTALL_TIMEOUT, check=False)
        except Exception as ex:
            logger("pm install (%s) fallo: %s" % (command[0], ex))
            continue

        output = (proc.stdout or b'').decode('utf-8', 'replace').strip()
        logger("pm install (%s): rc=%s %s" % (command[0], proc.returncode, output))

        if proc.returncode == 0 and 'Success' in output:
            return True

    return False


def launch_apk_installer(path):
    uri = 'file://' + urllib_parse.quote(path, safe='/')

    if is_espakodi_build():
        # The bridge in the APK itself, which does the conversion to content:// that Kodi 21
        # does not do. Without it, on EspaKodi the direct intent installs nothing.
        builtin = (f'StartAndroidActivity("espakodi.kodi","ekapk.install","","{uri}",'
                   f'"","","","","espakodi.kodi.EkApk")')
    else:
        builtin = ('StartAndroidActivity("", "android.intent.action.VIEW", '
                   '"application/vnd.android.package-archive", "%s", "1")' % uri)

    logger("Lanzando instalador de Android: %s" % builtin)
    xbmc.executebuiltin(builtin)


def open_unknown_sources_settings():
    xbmc.executebuiltin('StartAndroidActivity("", "android.settings.MANAGE_UNKNOWN_APP_SOURCES")')


def apk_post_download(dest, filename):
    if system_platform != 'android':
        xbmcgui.Dialog().ok(HEADING, translate_fmt(30060, filename, dest))
        return

    autoinstall = apk_autoinstall_supported()

    while True:
        options, actions = list(), list()

        if autoinstall:
            options.append(translate(30061))
            actions.append('install')

        options.append(translate(30062))
        actions.append('manual')
        options.append(translate(30063))
        actions.append('sources')

        if not autoinstall:
            # With no FileProvider the intent does not install, but with root or Kodi as a
            # system app pm install is still a way through
            options.append(translate(30068))
            actions.append('pm_install')

        options.append(translate(30064))
        actions.append('close')

        selected = xbmcgui.Dialog().select(translate(30065), options)
        if selected < 0:
            return

        action = actions[selected]

        if action == 'install':
            staged = stage_apk_public(dest)
            if not staged:
                continue
            launch_apk_installer(staged)
            return

        elif action == 'pm_install':
            staged = stage_apk_public(dest)
            if not staged:
                continue
            if try_pm_install(staged):
                xbmcgui.Dialog().ok(HEADING, translate(30069))
                return
            xbmcgui.Dialog().ok(HEADING, translate(30070))

        elif action == 'manual':
            xbmcgui.Dialog().ok(HEADING, translate_fmt(30055, dest))

        elif action == 'sources':
            open_unknown_sources_settings()
            return

        else:
            return


def sha256_of(path):
    import hashlib

    digest = hashlib.sha256()
    handle = xbmcvfs.File(path)
    try:
        while True:
            chunk = handle.readBytes(APK_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        handle.close()

    return digest.hexdigest()


def download_apk(filename, url, sha256=''):
    # Every click on the menu starts the plugin from scratch, so a python Lock would be
    # useless and the latch has to live in a Window property. Without it, two clicks in
    # a row write at the same time into the same .part and corrupt it
    window = xbmcgui.Window(10000)
    lock = 'ekhorus_downloading_%s' % filename

    if window.getProperty(lock) == 'true':
        xbmcgui.Dialog().notification(HEADING, translate_fmt(30071, filename), icon_path)
        return

    window.setProperty(lock, 'true')
    try:
        _download_apk(filename, url, sha256)
    finally:
        window.clearProperty(lock)


def _download_apk(filename, url, sha256=''):
    folder = xbmcgui.Dialog().browse(3, translate_fmt(30053, filename), 'files', '', False, False,
                                     default_apk_folder())
    if not folder:
        return

    if not folder_is_writable(folder):
        xbmcgui.Dialog().ok(HEADING, translate_fmt(30067, folder))
        return

    set_setting("last_apk_folder", folder)

    dest = join_path(folder, filename)
    partial = dest + '.part'

    if xbmcvfs.exists(dest):
        if apk_looks_valid(dest) is False:
            # It is corrupt, so we neither ask nor offer it; it is redone and that is that
            logger("El APK existente esta corrupto, se descarga de nuevo: %s" % dest, 'error')
            xbmcgui.Dialog().ok(HEADING, translate_fmt(30078, filename))
            xbmcvfs.delete(dest)
        else:
            redownload = xbmcgui.Dialog().yesno(HEADING, translate_fmt(30056, filename),
                                                nolabel=translate(30077), yeslabel=translate(30076))
            if not redownload:
                # The APK is already there and it is fine, so the install options are offered.
                # The other way would be stranding them or making them fetch 100 MB for nothing
                apk_post_download(dest, filename)
                return
            xbmcvfs.delete(dest)

    if xbmcvfs.exists(partial):
        xbmcvfs.delete(partial)

    message = translate_fmt(30054, filename)
    dp = xbmcgui.DialogProgress()
    dp.create(HEADING, message)

    try:
        download_to(url, partial, dp, message)
    except DownloadCanceled:
        dp.close()
        xbmcvfs.delete(partial)
        logger("Descarga cancelada por el usuario: %s" % filename)
        xbmcgui.Dialog().notification(HEADING, translate(30057), icon_path)
        return
    except Exception as ex:
        dp.close()
        xbmcvfs.delete(partial)
        logger("Error descargando %s: %s" % (filename, ex), 'error')
        xbmcgui.Dialog().ok(HEADING, translate_fmt(30058, filename, ex))
        return

    dp.close()

    # Last filter before calling it good. If the server did not send Content-Length
    # we could not check the size, so at least the ZIP is validated
    if apk_looks_valid(partial) is False:
        logger("El APK descargado esta corrupto: %s" % partial, 'error')
        xbmcvfs.delete(partial)
        xbmcgui.Dialog().ok(HEADING, translate_fmt(30079, filename))
        return

    # The hash only arrives if the manifest carries it. It is the only thing that tells
    # "it arrived whole" from "what was announced arrived". If it cannot be computed (a
    # read failure) we carry on: throwing away 100 MB over a local stumble is worse
    if sha256:
        try:
            descargado = sha256_of(partial)
        except Exception as ex:
            logger("No se pudo calcular el sha256 de %s: %s" % (partial, ex), 'error')
            descargado = ''

        if descargado and descargado != sha256:
            logger("sha256 no coincide en %s: %s en vez de %s" % (filename, descargado, sha256), 'error')
            xbmcvfs.delete(partial)
            xbmcgui.Dialog().ok(HEADING, translate_fmt(30079, filename))
            return

    # The final name is only given if the download finished whole. That way a half APK
    # never looks installable
    if not xbmcvfs.rename(partial, dest):
        if not xbmcvfs.copy(partial, dest):
            # Careful, returning the .part path is no good here. Android does not treat it
            # as an APK and we would offer to install something that cannot be installed
            logger("No se pudo dejar el APK como %s" % dest, 'error')
            xbmcvfs.delete(partial)
            xbmcgui.Dialog().ok(HEADING, translate_fmt(30080, filename))
            return
        xbmcvfs.delete(partial)

    logger("APK descargado en %s" % dest)
    apk_post_download(dest, filename)


def downloadFile(url, dest, dp=None):
    import socket
    from urllib.request import urlretrieve

    def _pbhook(numblocks, blocksize, filesize, url=None, dp=None):
        if not dp:
            return

        # dp.update() only accepts int. Besides, when the server does not send the size,
        # urlretrieve passes filesize = -1: without this guard the percentage came out
        # negative (or stuck at 100% after jumping to the exception) for the whole download.
        if filesize > 0:
            percent = int(min(numblocks * blocksize * 100 / filesize, 100))
        else:
            percent = 0

        dp.update(max(0, percent))

    # urlretrieve takes no timeout, so the socket one is set, to make a stuck download
    # end up cutting off instead of leaving the dialog hanging indefinitely.
    previo = socket.getdefaulttimeout()
    socket.setdefaulttimeout(HTTP_TIMEOUT * 3)
    try:
        urlretrieve(url, dest, lambda nb, bs, fs, url=url: _pbhook(nb, bs, fs, url, dp))
    finally:
        socket.setdefaulttimeout(previo)

    time.sleep(1)

    return xbmcvfs.Stat(dest).st_size()


def extractFile(source, dest):
    import tarfile
    import zipfile
    ret = True

    if tarfile.is_tarfile(source):
        tar = tarfile.open(source, "r:*")
        tar.extractall(dest)
        tar.close()

    elif zipfile.is_zipfile(source):
        zip = zipfile.ZipFile(source, 'r')
        zip.extractall(dest)
        zip.close()

    else:
        ret = False

    return ret


def install_acestream():
    ruta = ruta_zip = ruta_extract = url = None
    set_setting("install_acestream", '')
    set_setting("acestream_cachefolder", '')

    if not system_platform in ['linux', 'windows']:
        logger("install_acestream: system_platform = %s" % str((system_platform, arquitectura, root)))
        return

    elif system_platform == "windows":
        ruta = translatePath("special://home")
        ruta_zip = os.path.join(ruta, "userdata", "acestream_win.zip")
        ruta_extract = data_path
        url ="https://github.com/Carlesto/Horus/releases/download/ace/acestream_win.zip" # acestream_win

    elif arquitectura == "arm" or (arquitectura == "aarch" and root):
        ruta = translatePath("special://home")
        ruta_zip = os.path.join(ruta, "userdata", "acestream.tar.gz")
        ruta_extract = data_path
        url = "https://github.com/Carlesto/Horus/releases/download/ace/acestream_elec.tar.gz" # linaroNDK

    elif arquitectura == "x86" and root:
        ruta = translatePath("special://home")
        ruta_zip = os.path.join(ruta, "userdata", "acestream.tar.gz")
        ruta_extract = data_path
        url = "https://github.com/Carlesto/Horus/releases/download/ace/acestream_x86.tar.gz" # acestream_x86

    else:
        logger("install_acestream: motor externo system_platform = %s" % str((system_platform, arquitectura, root)))
        set_setting("install_acestream", 'motor externo')
        return


    dp = xbmcgui.DialogProgress()
    dp.create(HEADING, translate(30000))
    logger("Descargando Acestream...")

    try:
        downloadFile(url, ruta_zip, dp)
    except Exception as e:
        logger("Error descargando Acestream: %s" % e, 'error')
        dp.close()
        xbmcgui.Dialog().ok(HEADING, translate(30050))
        return

    dp.update(0, translate(30001))
    logger("Descarga Completa: %s" %ruta_zip)
    time.sleep(1)

    dp.update(33, translate(30002))
    if extractFile(ruta_zip, ruta_extract):
        logger("Archivos descomprimidos en %s" %ruta_extract)
    else:
        dp.update(100, translate(30003) %ruta_extract)
        logger("Error al descomprimir Archivos...")
        if os.path.exists(ruta_zip): os.remove(ruta_zip)
        time.sleep(2)
        dp.close()
        return

    dp.update(90, translate(30004))
    if os.path.exists(ruta_zip): os.remove(ruta_zip)
    logger("Limpiando Archivos...")

    dp.update(100, translate(30005))
    time.sleep(3)
    dp.close()
    if system_platform == "windows":
        set_setting("install_acestream", os.path.join(ruta_extract, 'acestream', 'engine'))
    else:
        set_setting("install_acestream", os.path.join(ruta_extract, 'acestream.engine'))


system_platform, arquitectura, root = get_system_platform()
logger((system_platform, arquitectura, root))

if system_platform == 'android':
    # It is left in the log whether the EspaKodi install bridge is available. It is the
    # first thing to look at when somebody says an APK will not install for them.
    logger(f"puente de instalacion de EspaKodi: {is_espakodi_build()}")
# The import goes last because Server is instantiated right here, with settings read.
from acestream.server import Server
server = Server(host=get_setting("ip_addr", "127.0.0.1"), port=engine_port())

# -*- coding: utf-8 -*-

import xbmc

from core import httptools, scrapertools, servertools
from platformcode import config, logger, platformtools
from lib import jsunpack


color_exec = config.get_setting('notification_exec_color', default='cyan')
el_srv = ('Sin respuesta en [B][COLOR %s]') % color_exec
el_srv += ('ResolveUrl[/B][/COLOR]')


def import_libs(module):
    import os, sys, xbmcaddon
    from core import filetools

    path = os.path.join(xbmcaddon.Addon(module).getAddonInfo("path"))
    addon_xml = filetools.read(filetools.join(path, "addon.xml"))

    if addon_xml:
        require_addons = scrapertools.find_multiple_matches(addon_xml, '(<import addon="[^"]+"[^\/]+\/>)')
        require_addons = list(filter(lambda x: not 'xbmc.python' in x and 'optional="true"' not in x, require_addons))

        for addon in require_addons:
            addon = scrapertools.find_single_match(addon, 'import addon="([^"]+)"')
            if xbmc.getCondVisibility('System.HasAddon("%s")' % (addon)):
                import_libs(addon)
            else:
                xbmc.executebuiltin('InstallAddon(%s)' % (addon))
                import_libs(addon)

        lib_path = scrapertools.find_multiple_matches(addon_xml, 'library="([^"]+)"')
        for lib in list(filter(lambda x: not '.py' in x, lib_path)):
            sys.path.append(os.path.join(path, lib))


def get_video_url(page_url, url_referer=''):
    logger.info("(page_url='%s')" % page_url)
    video_urls = []

    ini_page_url = page_url

    page_url = page_url.replace('//cloudemb.com/e/', '//streamsb.net/play/').replace('//cloudemb.com/d/', '//streamsb.net/play/')

    if '//tubesb.com/' in page_url:
        page_url = page_url.replace('//tubesb.com/e/', '//streamsb.net/play/').replace('//tubesb.com/d/', '//streamsb.net/play/')
    elif '//watchsb.com/' in page_url:
        page_url = page_url.replace('//watchsb.com/e/', '//streamsb.net/play/').replace('//watchsb.com/d/', '//streamsb.net/play/')
    elif '//viewsb.com/' in page_url:
        page_url = page_url.replace('//viewsb.com/e/', '//streamsb.net/play/').replace('//viewsb.com/d/', '//streamsb.net/play/')
    elif '//sbfast.com/' in page_url:
        page_url = page_url.replace('//sbfast.com/e/', '//streamsb.net/play/').replace('//sbfast.com/d/', '//streamsb.net/play/')
    elif '//sbfull.com/' in page_url:
        page_url = page_url.replace('//sbfull.com/e/', '//streamsb.net/play/').replace('//sbfull.com/d/', '//streamsb.net/play/')
    elif '//sbspeed.com/' in page_url:
        page_url = page_url.replace('//sbspeed.com/e/', '//streamsb.net/play/').replace('//sbspeed.com/d/', '//streamsb.net/play/')
    elif '//sblanh.com/' in page_url:
        page_url = page_url.replace('//sblanh.com/e/', '//streamsb.net/play/').replace('//sblanh.com/d/', '//streamsb.net/play/')
    elif '//sbanh.com/' in page_url:
        page_url = page_url.replace('//sbanh.com/e/', '//streamsb.net/play/').replace('//sbanh.com/d/', '//streamsb.net/play/')

    data = httptools.downloadpage(page_url).data

    if 'File Not Found' in data or 'File is no longer available' in data:
        return 'El fichero no existe o ha sido borrado'

    if not "text/javascript'>(eval" in data:
        import time
        from platformcode import platformtools
        espera = 5

        platformtools.dialog_notification('Cargando Streamsb', 'Espera requerida de %s segundos' % espera)
        time.sleep(int(espera))

        data = httptools.downloadpage(page_url).data

    if not "text/javascript'>(eval" in data:
        media_url = scrapertools.find_single_match(str(data), 'sources:.*?file.*?"(.*?)"')
        if 'master.m3u8' in str(media_url):
            video_urls.append(['.m3u8 ', media_url])
            video_urls = servertools.get_parse_hls(video_urls)
            return video_urls

    packed = scrapertools.find_single_match(data, r"'text/javascript'>(eval.*?)\n")
    if packed:
        unpacked = jsunpack.unpack(packed)

        video_srcs = scrapertools.find_single_match(unpacked, "sources:\s*\[[^\]]+\]")
        video_info = scrapertools.find_multiple_matches(video_srcs, r'{(file:.*?)}}')

        try:
           sub = scrapertools.find_single_match(unpacked, r'{file:"([^"]+)",label:"[^"]+",kind:"captions"')
        except:
           sub = ''

        for info in video_info:
            url = scrapertools.find_single_match(info, r'file:"([^"]+)"')

            if url:
                if url == sub: continue

                extension = scrapertools.get_filename_from_url(video_url)[-4:]
                if extension in ('.png`', '.jpg'): continue

                if extension == '.mpd':
                    video_urls.append(['mpd', url])
                else:
                    video_urls.append([sub, url])

    if not video_urls:
        if xbmc.getCondVisibility('System.HasAddon("script.module.resolveurl")'):
            try:
                import_libs('script.module.resolveurl')

                import resolveurl
                page_url = ini_page_url
                resuelto = resolveurl.resolve(page_url)

                if resuelto:
                    video_urls.append(['mp4', resuelto + '|Referer=%s' % page_url])
                    return video_urls

                platformtools.dialog_notification(config.__addon_name, el_srv, time=3000)

            except:
                import traceback
                logger.error(traceback.format_exc())
                platformtools.dialog_notification(config.__addon_name, el_srv, time=3000)

        else:
           return 'Acceso Denegado'

    return video_urls

# -*- coding: utf-8 -*-
# EKHorus - List and panel window, shared by EspaKodi Addons and Download APKs.
#
# The caller passes a function that returns the rows and another that says what to do
# when they are pressed; everything else (the panel following the focus, the text
# swiping, the remote navigation) lives here.

import collections
import threading

import xbmc
import xbmcgui

from lib.utils import echar_pestillo, logger, quitar_pestillo, runtime_path
from lib.ui_common import Deslizador

ID_LISTA = 200
ID_CERRAR = 100
ID_BOTON1 = 103
ID_BOTON2 = 104
ID_BARRA = 300
ID_TEXTO = 301

_PESTILLO = 'ekhorus.lista'
SONDEO_MS = 200

_ATRAS = (9, 10, 92)  # ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, ACTION_NAV_BACK

# pill: (text, 'on' | 'off' | 'gris'), or None if the row carries a loose value
Fila = collections.namedtuple(
    'Fila', 'clave titulo pista icono valor pastilla plot sep',
    defaults=('', '', '', None, '', False))

ORO = 'FFFFB70F'


class Pantalla(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titulo = ''
        self.subtitulo = ''
        self.estado = ''
        self.pista = ''          # remote legend, different on each screen
        self.botones = ()        # ((label, function), ...), up to two
        self.hacer_filas = None  # callable -> [Fila]
        self.al_pulsar = None    # callable(Fila) -> 'cerrar' closes, 'inicio' repaints at top
        self.al_volver = None    # callable() -> True if Back has gone up a level
        self.al_abrir = None     # callable(window) once painted
        self._filas = list()
        self._cerrando = False
        self._pintado = None
        self._dedo = None

    # --- life cycle --------------------------------------------------------------------

    def onInit(self):
        # Kodi may call here more than once (when reloading the skin); without this guard
        # the rows would be duplicated and a second thread would start.
        if self._filas:
            return

        self._dedo = Deslizador(self, ID_BARRA, ID_TEXTO)
        self.setProperty('pl_titulo', self.titulo)
        self.setProperty('pl_sub', self.subtitulo)
        self.setProperty('pl_estado', self.estado)
        self.setProperty('pl_pista', self.pista)
        for n, (etiqueta, _) in enumerate(self.botones[:2]):
            self.setProperty('pl_b1' if n == 0 else 'pl_b2', etiqueta)

        self._pintar(0, enfocar=True)
        self._refrescar_panel(forzar=True)

        if self.al_abrir is not None:
            self.al_abrir(self)

        threading.Thread(target=self._bucle_foco, daemon=True).start()

    def close(self):
        self._cerrando = True
        super().close()

    def set_cabecera(self, titulo=None, subtitulo=None, estado=None, pista=None):
        """Changes the texts at the top without touching the list.

        A multi-level window needs it, where the title says where you are."""
        for propiedad, valor in (('pl_titulo', titulo), ('pl_sub', subtitulo),
                                 ('pl_estado', estado), ('pl_pista', pista)):
            if valor is not None:
                self.setProperty(propiedad, valor)

    def repintar(self, seleccion=0):
        self._pintar(seleccion, enfocar=True)
        self._refrescar_panel(forzar=True)

    # --- painting ----------------------------------------------------------------------

    def _pintar(self, seleccion=None, enfocar=False):
        control = self.getControl(ID_LISTA)
        if seleccion is None:
            seleccion = control.getSelectedPosition()

        self._filas = list(self.hacer_filas())
        items = list()

        for fila in self._filas:
            item = xbmcgui.ListItem(label=fila.titulo)
            if fila.sep:
                item.setProperty('f_tipo', 'sep')
            else:
                item.setProperty('f_icono', fila.icono)
                item.setProperty('f_pista', fila.pista)
                if fila.pastilla:
                    item.setProperty('f_pastilla', fila.pastilla[0])
                    item.setProperty('f_estado', fila.pastilla[1])
                elif fila.valor:
                    item.setLabel2(fila.valor)
            items.append(item)

        control.reset()
        control.addItems(items)

        if 0 <= seleccion < len(items):
            control.selectItem(seleccion)

        if enfocar:
            self.setFocusId(ID_LISTA)

    def _refrescar_panel(self, forzar=False):
        if self.getFocusId() != ID_LISTA or not self._filas:
            return

        # The thread may read just while the main thread rebuilds the list, so the position
        # is checked against the rows before indexing.
        pos = self.getControl(ID_LISTA).getSelectedPosition()
        if not 0 <= pos < len(self._filas) or (pos == self._pintado and not forzar):
            return

        self._pintado = pos
        fila = self._filas[pos]
        self.setProperty('pl_titulo_panel', fila.titulo)
        self.setProperty('pl_plot', fila.plot)

    def _bucle_foco(self):
        monitor = xbmc.Monitor()

        while not self._cerrando and not monitor.abortRequested():
            try:
                self._refrescar_panel()
            except Exception as e:
                # The window may have been closed between the read and the painting
                logger(f'list_screen: bucle de foco: {e}')
            if monitor.waitForAbort(SONDEO_MS / 1000):
                break

    # --- actions -----------------------------------------------------------------------

    def onAction(self, action):
        if self._dedo is not None and self._dedo.accion(action):
            return

        # A Python WindowXMLDialog does not close by itself with Back.
        if action.getId() in _ATRAS:
            # With al_volver the window has several levels: Back goes up one, and only
            # closes when there is nowhere left to go up to. Without it, it behaves as
            # it always did.
            if self.al_volver is not None and self.al_volver():
                self.repintar()
                return

            self.close()

    def onClick(self, controlId):
        if controlId == ID_CERRAR:
            self.close()
            return

        if controlId in (ID_BOTON1, ID_BOTON2):
            n = 0 if controlId == ID_BOTON1 else 1
            if n < len(self.botones) and self.botones[n][1]() == 'refrescar':
                self.repintar()
            return

        if controlId != ID_LISTA or not self._filas:
            return

        pos = self.getControl(ID_LISTA).getSelectedPosition()
        if not 0 <= pos < len(self._filas):
            return

        fila = self._filas[pos]
        if fila.sep:
            return

        # A tap moves the selection and presses at the same time, so the panel thread may not
        # have seen the new row yet; it is painted here before doing anything.
        self._refrescar_panel(forzar=True)

        resultado = self.al_pulsar(fila)

        if resultado == 'cerrar':
            self.close()
            return

        # The focus is set here on purpose: on returning from a dialog it belongs to
        # the dialog just closed, and has to go back to the row it was left from. With
        # 'inicio' it is the other way round: the level has changed and the list is
        # another one, so keeping the position would leave the selection in the middle
        # of a new list.
        self.repintar(0 if resultado == 'inicio' else pos)


def mostrar(titulo, subtitulo, hacer_filas, al_pulsar, botones=(), estado='',
            pista='[B]OK[/B] abre    ·    [B]Derecha[/B] lee    ·    [B]Atrás[/B] cierra',
            al_volver=None, al_abrir=None):
    """Opens the window. Returns False if it could not, to fall back to the classic list."""
    if not echar_pestillo(_PESTILLO):
        logger('list_screen: ya hay una ventana abierta, no se abre otra')
        return True

    ventana = None
    try:
        # Inside the try: if it blew up while being built, the latch cannot stay closed
        ventana = Pantalla('ekhorus_lista.xml', runtime_path, 'Default', '1080i')
        ventana.titulo = titulo
        ventana.subtitulo = subtitulo
        ventana.estado = estado
        ventana.pista = pista
        ventana.botones = tuple(botones)[:2]
        ventana.hacer_filas = hacer_filas
        ventana.al_pulsar = al_pulsar
        ventana.al_volver = al_volver
        ventana.al_abrir = al_abrir
        ventana.doModal()
        return True

    except Exception as e:
        logger(f'list_screen: {e}', 'error')
        return False

    finally:
        if ventana is not None:
            ventana._cerrando = True
        # doModal does not free the controls, and in Kodi those are textures in memory
        del ventana
        quitar_pestillo(_PESTILLO)

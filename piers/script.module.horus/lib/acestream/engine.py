import os
import signal
import subprocess

from threading import Thread
from lib.acestream.object import Observable
from lib.utils import no_window


class Engine(Observable):
  def __init__(self, bin, **options):
    Observable.__init__(self)

    self.process = None
    self.bin     = bin
    self.options = options

  def start(self, daemon=True, **kwargs):
    if not self.running:
      thread = Thread(target=self._start_process, kwargs=kwargs)
      # setDaemon() was removed in Python 3.12
      thread.daemon = daemon
      thread.start()

  def stop(self):
    # The process is launched in a thread that sets self.process to None when it
    # ends, so a local reference avoids reading a None halfway through.
    process = self.process

    if not process:
      return

    try:
      os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception:
      try:
        # Windows has no killpg. If taskkill is missing too (unix without setsid),
        # fall back to Popen's own terminate() instead of propagating the error.
        subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)], **no_window())
      except Exception:
        try:
          process.terminate()
        except Exception as error:
          self.emit('error', str(error))

    self.process = None
    self.emit('terminated')

  @property
  def running(self):
    return bool(self.process)

  @property
  def process_args(self):
    if isinstance(self.bin, (list, tuple)):
      # Preferred form: the command already comes split. A path with spaces
      # ("C:\\Users\\Juan Perez\\...") cannot be split on spaces, and the previous
      # split() broke it in two, so the engine never started.
      options = [str(a) for a in self.bin]
    elif os.path.exists(self.bin):
      options = [self.bin]
    else:
      options = self.bin.split()

    for (key, value) in self.options.items():
      options.append('--{0}'.format(key.replace('_', '-')))

      if not isinstance(value, bool):
        options.append(str(value))

    return options

  def _start_process(self, **kwargs):
    try:
      kwargs['preexec_fn'] = os.setsid
    except:
      # CREATE_NO_WINDOW avoids the engine's black console over Kodi on Windows.
      kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    kwargs['stdout'] = subprocess.PIPE
    kwargs['stderr'] = subprocess.PIPE

    input = None
    if 'stdin' in kwargs:
      input = kwargs['stdin']
      kwargs['stdin'] = subprocess.PIPE

    try:
      try:
        self.process = subprocess.Popen(self.process_args, **kwargs)
      except RuntimeError:
        kwargs.pop('preexec_fn', None)
        kwargs.pop('creationflags', None)
        self.process = subprocess.Popen(self.process_args, **kwargs)

      self.emit('started')

      stdout, stderr = self.process.communicate(input)

      if stderr:
        self.emit('error::subprocess', str(stderr))

      self.process = None
      self.emit('terminated')
    except OSError as error:
      self.process = None
      self.emit('error', str(error))

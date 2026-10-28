# Brok the InvestiGator po polsku: reads the game's clipboard narration.
# Texts that have a Polish recording in the game's access folder are played with that recording
# (several in a row when the game joins texts); the rest (voice acting lines) is spoken by NVDA.
import globalPluginHandler
import addonHandler
import windowUtils
import api
import ui
import nvwave
import speech
import os
import re
import json
import time
import threading
from ctypes import windll
from logHandler import log
from scriptHandler import script
import queueHandler
from . import oggdecode

addonHandler.initTranslation()

WM_CLIPBOARDUPDATE = 0x031D
BROK_APP = "brokgame"
MAP_FILE = os.path.join(os.path.dirname(__file__), "brok_map.json")
UNMATCHED_COST = 1000


def norm(t):
	t = re.sub(r"<[^>]*>|\{[^}]*\}", " ", t)
	return re.sub(r"[\W_]+", "", t.lower())


def split_recordings(text, recordings, maxLen):
	"""Returns the recordings that together say text, or None if some words have no recording."""
	s = norm(text)
	n = len(s)
	if not n:
		return None
	if s in recordings:
		return [recordings[s]]
	inf = float("inf")
	best = [(inf, None)] * (n + 1)
	best[0] = (0, None)
	for i in range(n):
		cost = best[i][0]
		if cost == inf:
			continue
		if cost + UNMATCHED_COST < best[i + 1][0]:
			best[i + 1] = (cost + UNMATCHED_COST, (i, None))
		for j in range(min(n, i + maxLen), i + 1, -1):
			rec = recordings.get(s[i:j])
			if rec and cost + 1 < best[j][0]:
				best[j] = (cost + 1, (i, rec))
	if best[n][0] >= UNMATCHED_COST:
		return None
	recs = []
	j = n
	while j > 0:
		i, rec = best[j][1]
		recs.append(rec)
		j = i
	return recs[::-1]


def make_player(channels, rate):
	try:
		return nvwave.WavePlayer(channels=channels, samplesPerSec=rate, bitsPerSample=16)
	except TypeError:
		import config
		return nvwave.WavePlayer(channels=channels, samplesPerSec=rate, bitsPerSample=16,
			outputDevice=config.conf["audio"]["outputDevice"])


class RecordingPlayer(object):
	"""Plays audio files one after another; a new request stops the current one."""

	def __init__(self):
		self.generation = 0
		self.lock = threading.Lock()
		self.player = None

	def stop(self):
		with self.lock:
			self.generation += 1
			player = self.player
		if player:
			try:
				player.stop()
			except Exception:
				pass

	def play(self, paths):
		self.stop()
		threading.Thread(target=self._run, args=(paths, self.generation), daemon=True).start()

	def _run(self, paths, gen):
		for path in paths:
			if gen != self.generation:
				return
			reader = None
			try:
				reader = oggdecode.OggReader(path)
				player = make_player(reader.channels, reader.rate)
				with self.lock:
					if gen != self.generation:
						return
					self.player = player
				while gen == self.generation:
					data = reader.read()
					if not data:
						break
					player.feed(data)
				if gen == self.generation:
					player.idle()
				player.close()
				log.info("brokPolski: played %s" % os.path.basename(path))
			except Exception:
				log.error("brokPolski: cannot play %s" % path, exc_info=True)
				return
			finally:
				if reader:
					reader.close()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super(GlobalPlugin, self).__init__()
		self.enabled = True
		self.recordings = {}
		try:
			with open(MAP_FILE, encoding="utf-8") as f:
				self.recordings = json.load(f)
		except Exception:
			log.error("brokPolski: cannot load map", exc_info=True)
		self.maxLen = max([len(k) for k in self.recordings] or [0])
		self.accessDir = None
		self.player = RecordingPlayer()
		self.window = ClipboardMonitorWindow(plugin=self)
		windll.user32.AddClipboardFormatListener(self.window.handle)
		queueHandler.queueFunction(queueHandler.eventQueue, self.quietOtherClipboardReaders)

	def terminate(self):
		windll.user32.RemoveClipboardFormatListener(self.window.handle)
		self.window.destroy()
		self.player.stop()

	def quietOtherClipboardReaders(self):
		"""Other add-ons that read every clipboard change (clipReader) stay silent in Brok."""
		for plugin in list(globalPluginHandler.runningPlugins):
			if plugin is self or "clipreader" not in type(plugin).__module__.lower():
				continue
			original = getattr(plugin, "read", None)
			if not callable(original) or getattr(original, "_brokWrapped", False):
				continue

			def wrapped(data, _original=original):
				if self.enabled and self.brokAccessDir():
					return
				return _original(data)
			wrapped._brokWrapped = True
			plugin.read = wrapped
			log.info("brokPolski: %s is silent while Brok is in the foreground" % type(plugin).__module__)

	def brokAccessDir(self):
		"""Folder with the game's audio files when Brok is in the foreground, else None."""
		try:
			appModule = api.getForegroundObject().appModule
			if appModule.appName.lower() != BROK_APP:
				return None
			if not self.accessDir:
				self.accessDir = os.path.join(os.path.dirname(appModule.appPath), "access")
			return self.accessDir
		except Exception:
			return None

	def read(self, data):
		if not self.enabled:
			return
		accessDir = self.brokAccessDir()
		if not accessDir:
			return
		recs = split_recordings(data, self.recordings, self.maxLen) if self.recordings else None
		paths = [os.path.join(accessDir, *r.split("/")) for r in recs] if recs else None
		if paths and all(os.path.isfile(p) for p in paths):
			log.info("brokPolski: %d recording(s) for %r" % (len(paths), data[:60]))
			speech.cancelSpeech()
			self.player.play(paths)
		else:
			log.info("brokPolski: NVDA speaks %r" % data[:60])
			self.player.stop()
			ui.message(data)

	@script(
		# Translators: input help for the toggle command.
		description="Włącza lub wyłącza czytanie schowka w grze Brok the InvestiGator",
		category="Brok po polsku",
		gesture="kb:NVDA+shift+b",
	)
	def script_toggle(self, gesture):
		self.enabled = not self.enabled
		self.player.stop()
		ui.message("Brok: czytanie schowka włączone" if self.enabled else "Brok: czytanie schowka wyłączone")


class ClipboardMonitorWindow(windowUtils.CustomWindow):
	className = u'nvdaBrokPolskiClipboard'

	def __init__(self, windowName=None, plugin=None):
		super(ClipboardMonitorWindow, self).__init__(windowName)
		self.plugin = plugin

	def windowProc(self, hwnd, msg, wParam, lParam):
		if msg == WM_CLIPBOARDUPDATE:
			data = None
			for attempt in range(5):
				try:
					data = api.getClipData()
					break
				except (TypeError, PermissionError, OSError):
					time.sleep(0.01)
			if data:
				queueHandler.queueFunction(queueHandler.eventQueue, self.plugin.read, data)
			return 0
		return None

	def destroy(self):
		super(ClipboardMonitorWindow, self).destroy()
		self.plugin = None

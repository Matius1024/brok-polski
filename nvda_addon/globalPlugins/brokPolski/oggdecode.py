"""Minimal Ogg Vorbis decoder using the bundled libsndfile (ctypes, no NVDA imports)."""
import ctypes
import os

SFM_READ = 0x10


class SF_INFO(ctypes.Structure):
	_fields_ = [
		("frames", ctypes.c_int64),
		("samplerate", ctypes.c_int),
		("channels", ctypes.c_int),
		("format", ctypes.c_int),
		("sections", ctypes.c_int),
		("seekable", ctypes.c_int),
	]


_lib = None


def lib():
	global _lib
	if _lib is None:
		_lib = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libsndfile_x64.dll"))
		_lib.sf_wchar_open.restype = ctypes.c_void_p
		_lib.sf_wchar_open.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.POINTER(SF_INFO)]
		_lib.sf_readf_short.restype = ctypes.c_int64
		_lib.sf_readf_short.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
		_lib.sf_close.argtypes = [ctypes.c_void_p]
	return _lib


class OggReader(object):
	"""Reads 16-bit PCM chunks from an audio file."""

	def __init__(self, path):
		self.info = SF_INFO()
		self.handle = lib().sf_wchar_open(path, SFM_READ, ctypes.byref(self.info))
		if not self.handle:
			raise IOError("cannot open " + path)

	@property
	def channels(self):
		return self.info.channels

	@property
	def rate(self):
		return self.info.samplerate

	def read(self, frames=4096):
		buf = ctypes.create_string_buffer(frames * self.info.channels * 2)
		got = lib().sf_readf_short(self.handle, buf, frames)
		return buf.raw[:got * self.info.channels * 2]

	def close(self):
		if self.handle:
			lib().sf_close(self.handle)
			self.handle = None

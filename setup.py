from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
import numpy

setup(
	name = "accesscam",
    cmdclass = {'build_ext': build_ext},
	include_dirs = [numpy.get_include()],
    ext_modules = [Extension("bg2", ["bg2.pyx"]),Extension("ocr2", ["ocr2.pyx"]), Extension("hand2", ["hand2.pyx"])]
)
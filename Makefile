all: pyx

pyx: bg2.pyx ocr2.pyx hand2.pyx
	python setup.py build_ext --inplace

cleancfiles:
	rm -f bg2.c ocr2.c hand2.c

clean:
	rm -f bg2.pyd bg2.c ocr2.pyd ocr2.c hand2.pyd hand2.c


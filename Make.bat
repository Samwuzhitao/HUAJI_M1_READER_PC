pyinstaller -F -w -i ./image/zkxl.ico rfid_debug.py
del rfid_debug.spec
del *.pyc
rd /s /q build

# qpDown
**qpDown** is a simple m3u8 playlist downloader written in python
## requirements
- [ffmpeg](https://www.ffmpeg.org/download.html)
## installation
if you're not on a windows machine, you should create a virtual environment and enter it before installing the requirements
```
python -m pip install -r requirements.txt
```
## notes
> [!WARNING]
> to properly enable hwaccel on non-nvidia graphics card pc, please edit your ffmpeg hwaccel args on line 3 (main.py). you can google them for your os and gpu
## usage
**from pypi:**
```
qpdown -i ... -o ...
```
**from source:**
```
python main.py -i ... -o ...
```
## building
**requirements:**
- all packages in the **requirements.txt** file
- [pyinstaller](https://pypi.org/project/pyinstaller/)
```
python -m pyinstaller main.py --onefile
```
## contact
email: [q16@q16.dev](mailto:q16@q16.dev)

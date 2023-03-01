# BitratePlotter
A simple Python script to plot video bitrate graph using ffprobe, thus support the newest codec like HEVC, AV1

Mostly copied from [CrypticSignal/bitrate-plotter](https://github.com/CrypticSignal/bitrate-plotter)
# Mods
- Add fucntion to select file from gui, you can just use `python BitratePlotter.py` to start it
- Modify plot style
![example graph](https://github.com/XuebingZhao/BitratePlotter/blob/main/Figure_1.png)
- Merge 3 .py files to 1 .py file

# Requirements 
- Python 3.6+
- FFprobe executable in your PATH or in the same path to `BitratePlotter.y`.
- `pip install -r requirements.txt`

# Usage
You can find the output of `python BitratePlotter.py -h` below:
```
usage: python BitratePlotter.py [-h][ -f FILE_PATH ][-g {filled,unfilled}] [-gop] [-se SHOW_ENTRIES] [-ngm] [-s STREAM_SPECIFIER]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE_PATH, --file-path FILE_PATH
                        Enter the path of the file that you want to analyse. If the path contains a space, it must be
                        surrounded in double quotes. Example: -f "C:/Users/H/Desktop/my file.mp4"
  -g {filled,unfilled}, --graph-type {filled,unfilled}
                        Specify the type of graph that should be created. The default graph type is "unfilled". To see
                        the difference between a filled and unfilled graph, check out the example graph files.
  -gop                  Instead of plotting the bitrate every second, plot the bitrate of each GOP. This plots GOP end
                        time (x-axis, in seconds) against GOP bitrate (y-axis, kbps).
  -se SHOW_ENTRIES, --show-entries SHOW_ENTRIES
                        Only applicable if --no-graph-mode is specified. Use FFprobe's -show_entries option to specify
                        what to output. Example: -se frame=key_frame,pkt_pts_time
  -ngm, --no-graph-mode
                        Enable "no graph mode" which simply writes the output of ffprobe to a .txt file. You should
                        also use the --show-entries argument to specify what information you want ffprobe to output.
  -s STREAM_SPECIFIER, --stream-specifier STREAM_SPECIFIER
                        Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse.
                        The defaults for audio and video files are a:0 and V:0, respectively. Note that stream index
                        starts at 0. As an example, to target the 2nd audio stream, enter: --stream-specifier a:1
```

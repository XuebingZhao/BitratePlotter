# !/usr/bin/python3
# -*- coding: utf-8 -*-
# python -m nuitka --standalone --mingw64 --disable-console --file-version=0.1 --product-version=0.1 --company-name="StevenZhao" --product-name="BitratePlotter" --enable-plugin=tk-inter --include-data-file="C:/ffmpeg/bin/ffprobe.exe"=./ --output-dir=%USERPROFILE%/Desktop/nuikta-out BitratePlotter.py

from argparse import ArgumentParser
import io
import os
from pathlib import Path
import datetime
import subprocess

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplcursors

import tkinter as tk
import tkinter.filedialog as filedlg
import ctypes

LOGPIXELSX = 88
ctypes.windll.user32.SetProcessDPIAware()
scale = ctypes.windll.gdi32.GetDeviceCaps(ctypes.windll.user32.GetDC(0), LOGPIXELSX)/96
dpi = 163/scale

plt.rcParams['figure.dpi'] = dpi
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['figure.figsize'] = [8, 4]
plt.rcParams['figure.constrained_layout.use'] = True
plt.rcParams['font.sans-serif'] = ["Microsoft Yahei"]


def calc_number_of_frames(file_path, stream_specifier, file_duration):
    cmd = [
        'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()),
        '-select_streams', stream_specifier,
        '-show_entries', 'stream=r_frame_rate', '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    process = subprocess.run(cmd, capture_output=True)
    output = process.stdout.decode('utf-8')
    numerator, denominator = output.split('/')
    framerate = int(numerator) / int(denominator)
    number_of_frames = framerate * file_duration
    return number_of_frames


def get_file_duration(file_path, stream_specifier):
    duration_cmd = [
        'ffprobe', '-v', 'error', '-threads', str(os.cpu_count()),
        '-select_streams', stream_specifier,
        '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
        file_path
    ]
    process = subprocess.run(duration_cmd, capture_output=True)
    return float(process.stdout.decode('utf-8'))


def clear_current_line_in_terminal():
    width, height = os.get_terminal_size()
    print('\r' + ' ' * (width - 1) + '\r', end='')


def write_to_txt_file(filename, data, mode='a'):
    with open(filename, mode) as f:
        f.write(data)


def get_bitrate_every_second(process, file_duration):
    x_axis_values = []
    bitrate_every_second = []
    megabits_this_second = 0
    # Initially, get the bitrate for the first second.
    # After every second, this value is incremented by 1 so we can get the bitrate for the 2nd second, 3rd second, etc.
    time_to_check = 1
    # Initialise a dictionary where the decoding timestamps (DTS) will be the keys and the packet sizes will be the values.
    dts_times_and_packet_sizes = {}

    for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
        # ffprobe will return the time in ms and the size in bytes.
        dts_time, packet_size = line.strip().split(",")
        packet_size = int(packet_size)
        # Convert to megabits.
        packet_size = (packet_size * 8) / 1000_000

        try:
            float(dts_time)
        except Exception:
            pass
        else:
            dts_times_and_packet_sizes[float(dts_time)] = packet_size
            percentage_complete = round(((float(dts_time) / file_duration) * 100.0), 1)
            print(f"Progress: {percentage_complete}%", end="\r")

    if not gui:
        clear_current_line_in_terminal()  # Clears the progress and ETA.
    print("Done!")
    # Create a new dictionary where the entries are ordered by timestamp value (ascending order).
    ordered_dict = dict(sorted(dts_times_and_packet_sizes.items()))
    print("Calculating the bitrates...")

    for dts_time, packet_size in ordered_dict.items():
        if dts_time >= time_to_check:
            x_axis_values.append(dts_time)
            bitrate_every_second.append(megabits_this_second)

            percentage_complete = round(100.0 * (dts_time / file_duration), 1)
            print(f'Progress: {percentage_complete}%', end='\r')
            # write_to_txt_file(
            #     raw_data_filename, f"Timestamp: {dts_time} --> {round(megabits_this_second)} Mbps\n"
            # )

            megabits_this_second = packet_size
            time_to_check += 1
        else:
            megabits_this_second += packet_size

    if not gui:
        clear_current_line_in_terminal()
    return x_axis_values, bitrate_every_second


def get_gop_bitrates(process, number_of_frames, data_output_path):
    frame_count = 0
    keyframe_count = 0
    gop_length = 0
    gop_size = 0
    gop_end_times = []
    gop_bitrates = []

    for line in io.TextIOWrapper(process.stdout):
        frame_count += 1
        write_to_txt_file(data_output_path, line)

        key_frame, pkt_dts_time, pkt_size = line.strip().split(",")
        # Convert from bytes to megabits.
        pkt_size = (int(pkt_size) * 8) / 1000_000

        try:
            float(pkt_dts_time)
        except Exception:
            pass
        else:
            pkt_dts_time = float(pkt_dts_time)
            # key_frame=1 (with H.264, this is an IDR frame).
            if key_frame == "1":
                keyframe_count += 1

                if keyframe_count == 1:
                    gop_length = 1
                    gop_size += pkt_size
                    previous_pkt_dts_time = pkt_dts_time
                else:
                    gop_end_times.append(pkt_dts_time)
                    gop_duration = pkt_dts_time - previous_pkt_dts_time
                    gop_bitrates.append(gop_size / gop_duration)

                    previous_pkt_dts_time = pkt_dts_time
                    gop_size = pkt_size
                    # We've reached a new keyframe, set gop_length to 1.
                    gop_length = 1

            # key_frame=0
            else:
                gop_length += 1
                gop_size += pkt_size

            percentage_progress = round((frame_count / number_of_frames) * 100, 1)
            print(f"Progress: {percentage_progress}%", end="\r")

    return gop_end_times, gop_bitrates


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-f",
        "--file-path",
        type=str,
        # required=True,
        help="Enter the path of the file that you want to analyse. "
             "If the path contains a space, it must be surrounded in double quotes. "
             'Example: -f "C:/Users/H/Desktop/my file.mp4"',
    )
    parser.add_argument(
        "-g",
        "--graph-type",
        choices=["filled", "unfilled"],
        default="unfilled",
        help='Specify the type of graph that should be created. The default graph type is "unfilled". '
             "To see the difference between a filled and unfilled graph, check out the example graph files.",
    )
    parser.add_argument(
        "-gop",
        action="store_true",
        help="Instead of plotting the bitrate every second, plot the bitrate of each GOP. "
             "This plots GOP end time (x-axis, in seconds) against GOP bitrate (y-axis, Mbps).",
    )
    parser.add_argument(
        "-se",
        "--show-entries",
        type=str,
        default="packet=dts_time,size",
        help="Only applicable if --no-graph-mode is specified. "
             "Use FFprobe's -show_entries option to specify what to output. Example: -se frame=key_frame,pkt_pts_time",
    )
    parser.add_argument(
        "-ngm",
        "--no-graph-mode",
        action="store_true",
        help='Enable "no graph mode" which simply writes the output of ffprobe to a .txt file. '
             "You should also use the --show-entries argument to specify what information you want ffprobe to output.",
    )
    parser.add_argument(
        "-s",
        "--stream-specifier",
        type=str,
        help="Use FFmpeg stream specifier syntax to specify the audio/video stream that you want to analyse. "
             "The defaults for audio and video files are a:0 and V:0, respectively. "
             "Note that stream index starts at 0. "
             "As an example, to target the 2nd audio stream, enter: --stream-specifier a:1",
    )

    args = parser.parse_args()

    if args.file_path is None:
        rt = tk.Tk()
        rt.withdraw()
        file_path = filedlg.askopenfilename(title="Choose Video File",
                                        filetypes=[("MPEG-4", '*.mp4;*.m4v'),
                                                   ("Matroska", '*.mkv'),
                                                   ("All Files", '*')],
                                        initialdir="./")
        rt.destroy()
        gui = True
    else:
        file_path = args.file_path
        gui = False

    filename = Path(file_path).name
    filename_without_ext = Path(file_path).stem

    # This command will information about file's first stream.
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-threads",
        str(os.cpu_count()),
        "-show_streams",
        "-select_streams",
        "0",
        file_path,
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    first_stream = process.stdout.read().decode("utf-8").replace("\r", "").split("\n")

    if not args.stream_specifier:
        if "codec_type=video" in first_stream:
            print("Video file detected. The video stream will be analysed.")
            stream_specifier = "V:0"
        elif "codec_type=subtitle" in first_stream:
            print(
                "It seems like you have specified a video file. The video stream will be analysed.\n"
                "If this is not what you want, re-run this program using the -s argument "
                "to manually specify the stream to analyse."
            )
            stream_specifier = "V:0"
        else:
            stream_specifier = "a:0"
            print(
                "It seems like you have specified an audio file. The first audio stream will be analysed."
            )
    else:
        stream_specifier = args.stream_specifier
        print(f"The bitrate of stream {args.stream_specifier} will be analysed.")

    file_duration = get_file_duration(file_path, stream_specifier)

    if "V" in stream_specifier or "v" in stream_specifier:
        number_of_frames = calc_number_of_frames(file_path, stream_specifier, file_duration)

    # To calculate the bitrate every second, FFprobe needs to output the following entries.
    entries = "packet=dts_time,size"

    if args.no_graph_mode:
        entries = args.show_entries
    elif args.gop:
        entries = "frame=key_frame,pkt_dts_time,pkt_size"

    # The FFprobe command that will output the timestamps and packet sizes in CSV format.
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-threads",
        str(os.cpu_count()),
        "-select_streams",
        stream_specifier,
        "-show_entries",
        entries,
        "-of",
        "csv=print_section=0:nk=1",
        file_path,
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    if args.gop:
        data_output_path = f"[{filename}]/Keyframes & GOPs.txt"
        os.makedirs(f"[{filename}]", exist_ok=True)
        with open(data_output_path, "w"):
            pass

        gop_end_times, gop_bitrates = get_gop_bitrates(process, number_of_frames, data_output_path)

        plt.suptitle(filename)
        plt.xlabel("GOP end time (s)")
        plt.ylabel("GOP bitrate (Mbps)")

        if args.graph_type == "filled":
            plt.fill_between(gop_end_times, gop_bitrates)

        plt.stem(gop_end_times, gop_bitrates)
        # Use mplcursors to show the X and Y value when hovering over a point on the line.
        cursor = mplcursors.cursor(hover=True)
        cursor.connect(
            "add",
            lambda sel: sel.annotation.set_text(
                f"{round(sel.target[0], 1)}, {round(sel.target[1], 1)}"
            ),
        )
        print("Done! The graph will open in a new window.")
        plt.show()

    else:
        if args.no_graph_mode:
            ffprobe_output_path = f"{filename} (FFprobe Data)/{entries}.txt"
            os.makedirs(f"{filename} (FFprobe Data)", exist_ok=True)
            frame_count = 0
            # GOP length in terms of number of frames.
            gop_length = 0
            print("-----------------------------------------------------------------------------------")
            print(f"{args.show_entries} data is being written to /{ffprobe_output_path}...")

            if "key_frame" in args.show_entries or "pict_type" in args.show_entries:
                for line in io.TextIOWrapper(process.stdout):
                    frame_count += 1
                    percentage_progress = round((frame_count / number_of_frames) * 100, 1)
                    print(f"Progress: {percentage_progress}%", end="\r")
                    gop_length += 1
                    if (
                            "1" in line.strip().split(",")
                            or "I" in line.strip().split(",")
                            or "Iside_data" in line.strip().split(",")
                    ):
                        print("-----------------------------------------------------------------------")
                        print(f"Frame {frame_count} is an I-frame")

                        if gop_length != 1:
                            print(f"GOP length was {gop_length} frames")

                        # We have reached the next keyframe, set gop_length to 0 to calculate the next GOP length.
                        gop_length = 0
            else:
                for line in io.TextIOWrapper(process.stdout, encoding="utf-8"):
                    write_to_txt_file(ffprobe_output_path, line)
            print(f"Done! Check out the following path: /{ffprobe_output_path}")

        else:
            # timestamp_bitrate_file = f"[{filename}]/BitrateEverySecond.txt"
            # os.makedirs(f"[{filename}]", exist_ok=True)
            # with open(timestamp_bitrate_file, "w"):
            #     pass
            # Parse the ffprobe output save the timestamps and bitrates in the time_data and size_data lists, respectively.
            time_axis, bitrate_every_second = get_bitrate_every_second(
                process, file_duration
            )

            time_axis = [(datetime.datetime(2000, 1, 1, 0, 0, 0) + datetime.timedelta(seconds=i)) for i in time_axis]

            ave_bitrate = round(sum(bitrate_every_second) / len(bitrate_every_second), 3)
            max_bitrate = round(max(bitrate_every_second), 3)

            # write_to_txt_file(
            #     timestamp_bitrate_file,
            #     f"\nMin Bitrate: {min_bitrate} Mbps\nMax Bitrate: {max_bitrate} Mbps",
            # )

            print("Creating the graph...")
            fig, ax = plt.subplots()
            ax.set_title(f"{filename}\nAverage/Max Bitrate: {ave_bitrate}/{max_bitrate} Mbps")
            ax.set_xlabel("Time (s)")
            ax.set_xlim(min(time_axis), max(time_axis))
            locator = mdates.AutoDateLocator()
            formatter = mdates.DateFormatter("%H:%M:%S")
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
            ax.set_ylabel("Bitrate (Mbps)")
            ax.set_ylim(0, max_bitrate*1.1)
            ax.grid(which='both', axis='y')
            if args.graph_type == "filled":
                ax.fill_between(time_axis, bitrate_every_second)
            else:
                ax.plot(time_axis, bitrate_every_second, lw=1.5)
            plt.axhline(ave_bitrate, c="k", ls=":")
            plt.axhline(max_bitrate, c="orange", ls="--", lw=1.2)
            print("Done! The graph will open in a new window.")
            plt.show()


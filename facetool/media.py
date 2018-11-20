from glob import glob
import ffmpeg
import os
import logging

logger = logging.getLogger(__name__)

FRAME_FILENAME_LENGTH = 4

def _getwh(path):
    data = probe(path)
    width = data["streams"][0]["width"]
    height = data["streams"][0]["height"]
    wh = f"{width}x{height}"
    return wh

def _run(cmd):
    command = " ".join(cmd.compile())
    logging.debug(command)
    cmd.run()

"""
Does something like this:

ffmpeg -r 24.89 -f image2 -s 480x360 -i "video-in/%04d.jpg" -vcodec libx264 -crf 25 -pix_fmt yuv420p movie.mp4

"""
def combineframes(inp, out, framerate):
    if os.path.isdir(inp):
        path = f"{inp}/%04d.jpg"

    # Use the first file to get wh
    first_file = list(glob(f"{inp}/*"))[0]
    wh = _getwh(first_file)

    cmd = ffmpeg.input(path,
        r = framerate,
        f = "image2",
        s = wh
    ).output(out,
        vcodec = "libx264",
        crf = "25",
        pix_fmt = "yuv420p"
    )

    _run(cmd)

def extractframes(inp, out):
    data = probe(inp)
    output = f"{out}/%{FRAME_FILENAME_LENGTH}d.jpg"
    cmd = ffmpeg.input(inp).output(output, **{"q:v" : 2})
    _run(cmd)

def probe(inp = None):
    return ffmpeg.probe(inp)
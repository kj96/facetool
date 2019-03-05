#!/usr/bin/env python3
from facetool import config, media, util
from facetool.path import Path
from facetool.profiler import Profiler
from facetool.constants import *

from tqdm import tqdm
import argparse
import logging
import json
import os
import pandas as pd
import pdb

COMMANDS = (
    "average",
    "classify",
    "combineframes",
    "count",
    "crop",
    "extractframes",
    "landmarks",
    "locate",
    "pose",
    "probe",
    "swap",
)

OUTPUT_FORMAT_CHOICES = (
    "default",
    "csv",
    "json"
)

logger = logging.getLogger(__name__)

# Note that we always profile, we just don't print the output if the
# option is not enabled
profiler = Profiler("facetool.py")

def get_parser():
    parser = argparse.ArgumentParser(description = "Manipulate faces in videos and images")

    # Essentials
    parser.add_argument("command", choices = COMMANDS, nargs = "?")
    parser.add_argument("-i", "--input", type = str,
        required = True,
        help = "Input file or folder, 'face' when swapping"
    )
    parser.add_argument("-o", "--output", type = str,
        help = "Output file or folder",
        default = None
    )
    parser.add_argument("-t", "--target", type = str,
        help = "'Head' when swapping"
    )

    # Extra arguments
    parser.add_argument("-bl", "--blur", type = float,
        default = BLUR_AMOUNT,
        help = "Amount of blur to use during colour correction"
    )
    parser.add_argument("-dd", "--data-directory", type = str,
        default = DATA_DIRECTORY,
        help = "Directory where the data files are located"
    )
    parser.add_argument("-fr", "--framerate", type = str,
        default = DEFAULT_FRAMERATE
    )
    parser.add_argument("-fa", "--feather", type = int,
        default = FEATHER_AMOUNT,
        help = "Softness of edges on a swapped face"
    )
    parser.add_argument("-kt", "--keep-temp", action = "store_true",
        help = "Keep temporary files (used with video swapping"
    )
    parser.add_argument("--no-eyesbrows", action = "store_true")
    parser.add_argument("--no-nosemouth", action = "store_true")
    parser.add_argument("-of", "--output-format",
        choices = OUTPUT_FORMAT_CHOICES,
        help = "Specify output format"
    )
    parser.add_argument("-pp", "--predictor-path", type = str,
        default = PREDICTOR_PATH
    )
    parser.add_argument("--profile", action = "store_true",
        help = "Show profiler information"
    )
    parser.add_argument("-s", "--swap", action = "store_true",
        help = "Swap input and target"
    )
    parser.add_argument("-v", "--verbose", action = "store_true",
        help = "Show debug information"
    )
    parser.add_argument("-vv", "--extra-verbose", action = "store_true",
        help = "Show debug information AND raise / abort on exceptions"
    )

    return parser

def main(args):
    if args.verbose or args.extra_verbose:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug(args)

    config.PROFILE = args.profile
    config.VERBOSE = args.verbose or args.extra_verbose

    # Check for invalid argument combinations
    if args.output_format == "csv" and not args.output:
        raise Exception("With CSV as output format, a filename (-o) is required")

    # Swap around input and target
    if args.swap:
        args.input, args.target = args.target, args.input

    # Okay, the main stuff, get the command
    # Extract all frames from a movie to a set of jpg files
    if args.command == "extractframes":
        util.mkdir_if_not_exists(args.output)
        media.extractframes(args.input, args.output)

    # Combine all frames from a set of jpg files to a movie
    elif args.command == "combineframes":
        media.combineframes(args.input, args.output, framerate = args.framerate)

    # Show metadata on a media file
    elif args.command == "probe":
        data = media.probe(args.input)
        jsondata = json.dumps(data, indent = 4)
        print(jsondata)

    elif args.command == "landmarks":
        from facetool.landmarks import Landmarks

        landmarks = Landmarks(predictor_path = args.predictor_path)

        save_data = args.output_format and args.output_format != "default"

        if save_data:
            data = []

        # Check if we *could* have an output directory, and if so,
        # create it
        if args.output and Path(args.output).could_be_dir():
            Path(args.output).mkdir_if_not_exists()

        for pathobj in Path(args.input).images():
            path = str(pathobj)
            logging.debug(f"Processing {path}")

            print(f"Getting landmarks of {path}")

            if not args.output:
                outpath = None
            else:
                out = Path(args.output)

                if out.is_dir():
                    outpath = f"{out}/{Path(path).name}"
                else:
                    outpath = str(out)

            try:
                marks = landmarks.get_landmarks(str(path), outpath = outpath)
            except Exception as e:
                util.handle_exception(e, reraise = args.extra_verbose)

            if marks and save_data:
                points = [str(path)]
                [points.extend([m.x, m.y]) for m in marks]
                data.append(points)

            print(path, marks)

        if save_data:
            df = pd.DataFrame(data)

            if args.output_format == "csv":
                df.to_csv(args.output)
            elif args.output_format == "json":
                df.to_json(args.output)
            else:
                raise Exception(f"Invalid output format: {args.output_format}")

    elif args.command == "pose":
        from facetool.poser import Poser

        poser = Poser(predictor_path = args.predictor_path)

        # Check if we *could* have an output directory, and if so,
        # create it
        if args.output and Path(args.output).could_be_dir():
            Path(args.output).mkdir_if_not_exists()

        for pathobj in Path(args.input).images():
            path = str(pathobj)
            logging.debug(f"Processing {path}")

            if not args.output:
                outpath = None
            else:
                out = Path(args.output)

                if out.is_dir():
                    outpath = f"{out}/{Path(path).name}"
                else:
                    outpath = str(out)

            try:
                poses = poser.get_poses(path, outpath = outpath)
            except Exception as e:
                util.handle_exception(e, reraise = args.extra_verbose)

            print(f"{path}: {poses}")

    elif args.command == "count":
        from facetool.detect import Detect

        detect = Detect()

        if args.output_format == "csv":
            csv = []

        for path in Path(args.input).images():
            try:
                count = detect.count(path)
            except Exception as e:
                util.handle_exception(e, reraise = args.extra_verbose)

            print(f"Number of faces in '{path}': {count}")

            if args.output_format == "csv":
                csv.append({
                    "path" : path,
                    "count" : count
                })

        if args.output_format == "csv":
            df = pd.DataFrame(csv)
            df.to_csv(args.output)

    elif args.command == "locate":
        from facetool.detect import Detect

        detect = Detect()

        for path in Path(args.input).images():
            to_directory = os.path.isdir(args.input)
            locations = detect.locate(path, args.output, to_directory = to_directory)
            print(locations)

    elif args.command == "crop":
        from facetool.detect import Detect

        detect = Detect()

        for path in Path(args.input).images():
            print(f"Cropping <{path}>")

            try:
                detect.crop(str(path), args.output)
            except Exception as e:
                util.handle_exception(e, reraise = args.extra_verbose)

    elif args.command == "classify":
        from facetool.classifier import Classifier

        classifier = Classifier(
            data_directory = args.data_directory,
            output_format = args.output_format,
            predictor_path = args.predictor_path
        )

        for path in Path(args.input).images():
            print(f"Classifying <{path}>")

            try:
                classifier.classify(str(path))
            except Exception as e:
                util.handle_exception(e, reraise = args.extra_verbose)

        if args.output_format == "csv":
            classifier.to_csv(args.output)

    elif args.command == "average":
        from facetool.averager import Averager

        profiler.tick("start averaging")

        averager = Averager()

        averager.average(args.input, args.output)

        profiler.tick("done averaging")

    elif args.command == "swap":
        from facetool.swapper import Swapper

        profiler.tick("start swapping")
        # First check if all arguments are given
        arguments = [args.input, args.target]

        if not all(arguments + [args.output]):
            raise Exception("Input, target and output are required for swapping")

        # And if these things are paths or files
        if not all([os.path.exists(a) for a in arguments]):
            raise Exception("Input and target should be valid files or directories")

        pbar = tqdm()

        def update_pbar():
            pbar.total = swapper.filecount
            pbar.update()

            if args.verbose:
                pbar.write(swapper.last_message)

        # That is out of the way, set up the swapper
        swapper = Swapper(
            predictor_path = args.predictor_path,
            feather = args.feather,
            blur = args.blur,
            reraise_exceptions = args.extra_verbose,
            keep_temp = args.keep_temp,
            overlay_eyesbrows = not args.no_eyesbrows,
            overlay_nosemouth = not args.no_nosemouth,
            reporthook = update_pbar
        )

        # Directory of faces to directory of heads
        if Path(args.input).is_dir() and Path(args.target).is_dir():
            swapper.swap_directory_to_directory(args.input, args.target, args.output)

        # Face to directory of heads
        elif media.is_image(args.input) and Path(args.target).is_dir():
            swapper.swap_image_to_directory(args.input, args.target, args.output)

        # Directory of faces to head
        elif Path(args.input).is_dir() and media.is_image(args.target):
            swapper.swap_directory_to_image(args.input, args.target, args.output)

        # Face in image to video
        elif media.is_video(args.target) and media.is_image(args.input):
            swapper.swap_image_to_video(args.target, args.input, args.output)

        # Face of video to head in other video
        elif media.is_video(args.target) and media.is_video(args.input):
            swapper.swap_video_to_video(args.target, args.input, args.output)

        # Image to image
        elif media.is_image(args.target) and media.is_image(args.input):
            swapper.swap_image_to_image(args.target, args.input, args.output)

        # I don't even know if there is an option that isn't in the list above,
        # but if it isn't, you'll get this
        else:
            raise Exception("Invalid swap options")

        pbar.close()
        profiler.tick("done swapping")
    else:
        # No arguments, just display help
        parser.print_help()

if __name__ == "__main__":
    parser = get_parser()
    args = parser.parse_args()

    try:
        main(args)
    except Exception as e:
        util.handle_exception(e, reraise = args.extra_verbose)

    if config.PROFILE:
        profiler.dump_events()
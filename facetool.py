#!/usr/bin/env python3
from dataknead import Knead
from facetool import config, media, util
from facetool.constants import *
from facetool.path import Path
from facetool.profiler import Profiler
from facetool.errors import ArgumentError
from facetool.util import message, force_mkdir, sample_remove, is_json_path

from random import random
from tqdm import tqdm
import argparse
import logging
import json
import os
import pandas as pd
import pdb
import shutil
import sys

COMMANDS = (
    "average",
    "classify",
    "cluster",
    "combineaudio",
    "combineframes",
    "count",
    "distance",
    "crop",
    "encode",
    "extractframes",
    "landmarks",
    "locate",
    "pose",
    "probe",
    "sample",
    "swap",
)

OUTPUT_FORMAT_CHOICES = (
    "default",
    "csv",
    "json"
)

SWAP_METHODS = [
    "faceswap",
    "faceswap3d"
]

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
    parser.add_argument("-ai", "--audio-input", type = str,
        default = None,
        help = "Add a separate audio file with the end result movie"
    )
    parser.add_argument("--as-percentage", action = "store_true",
        help = "Show face distances as percentages"
    )
    parser.add_argument("-bl", "--blur", type = float,
        default = BLUR_AMOUNT,
        help = "Amount of blur to use during colour correction"
    )
    parser.add_argument("-dd", "--data-directory", type = str,
        default = DATA_DIRECTORY,
        help = "Directory where the data files are located"
    )
    parser.add_argument("-f", "--force", action = "store_true",
        help = "Force commands and ignore warnings, like with sample"
    )
    parser.add_argument("-fr", "--framerate", type = str,
        default = DEFAULT_FRAMERATE
    )
    parser.add_argument("-fa", "--feather", type = int,
        default = FEATHER_AMOUNT,
        help = "Softness of edges on a swapped face"
    )
    parser.add_argument("-if", "--ignore-nofaces", action = "store_true",
        default = False,
        help = "When having no faces to swap, keep the original input image"
    )
    parser.add_argument("-ih", "--image-height", type = int,
        default = DEFAULT_IMAGE_HEIGHT,
        help = "Height of output image / height"
    )
    parser.add_argument("-iw", "--image-width", type = int,
        default = DEFAULT_IMAGE_WIDTH,
        help = "Width of output image / video"
    )
    parser.add_argument("-kt", "--keep-temp", action = "store_true",
        help = "Keep temporary files (used with video swapping)"
    )
    parser.add_argument("-m", "--model", type = str,
        help = "Use a precalculated model (for calculating distances)"
    )
    parser.add_argument("--no-audio", action = "store_true")
    parser.add_argument("-nocc", "--no-colour-correct", action = "store_true",
        help = "Don't colour correct"
    )
    parser.add_argument("--no-eyesbrows", action = "store_true")
    parser.add_argument("--no-nosemouth", action = "store_true")
    parser.add_argument("--no-threading", action = "store_true",
        help = "Don't use multithreading"
    )
    parser.add_argument("--only-mouth", action="store_true")
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
    parser.add_argument("-q", "--quiet", action = "store_true",
        help = "Don't print output to the console"
    )
    parser.add_argument("-s", "--swap", action = "store_true",
        help = "Swap input and target"
    )
    parser.add_argument("--save-originals", action = "store_true",
        help = "Save original images when averaging faces"
    )
    parser.add_argument("--save-warped", action = "store_true",
        help = "Save warped images when averaging faces"
    )
    parser.add_argument("--swap-method",
        choices = SWAP_METHODS,
        default = SWAP_METHODS[0],
        help = f"Swap method for faceswap (options are: {SWAP_METHODS}"
    )
    parser.add_argument("-so", "--swap-order", type = str,
        help = "Comma-separated list with order of faceswaps on target, implies a multiswap"
    )
    parser.add_argument("-sp", "--sample-percentage", type = float,
        help = "Percentage of files in a directory to randomly remove (used for the sample command)"
    )
    parser.add_argument("-sr", "--swap-order-repeat", action = "store_true", default = False,
        help = "When using --swap-order and there are not enough target faces, repeat the sequence"
    )
    parser.add_argument("--temp-dir", type = str,
        help = "Define the directory where temporary files should be placed"
    )
    parser.add_argument("-v", "--verbose", action = "store_true",
        help = "Show debug information"
    )
    parser.add_argument("-vv", "--extra-verbose", action = "store_true",
        help = "Show debug information AND raise / abort on exceptions"
    )
    parser.add_argument("--warp-3d", action="store_true",
        help = "Swap faces and morph to coordinates of target face"
    )
    return parser

def main(args):
    if args.verbose or args.extra_verbose:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug(args)

    config.PROFILE = args.profile
    config.QUIET = args.quiet
    config.VERBOSE = args.verbose or args.extra_verbose

    # Check for invalid argument combinations
    if any([args.output_format == "csv", args.output_format == "json"]) and not args.output:
        raise ArgumentError("With CSV as output format, a filename (-o) is required")

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

    # Combine audio with an input movie
    elif args.command == "combineaudio":
        media.combineaudio(args.input, args.audio_input, args.output)

    # Randomly remove (sample) a percentage of files from a given directory
    elif args.command == "sample":
        if not args.sample_percentage:
            raise ArgumentError("The sample command needs a sample percentage (-sp)")

        sample_remove(args.input, args.sample_percentage, force_delete = args.force)

    # Show metadata on a media file
    elif args.command == "probe":
        try:
            data = media.probe(args.input)
        except:
            raise ArgumentError(f"Could not probe '{args.input}', probably not a video/image file")
        else:
            jsondata = json.dumps(data, indent = 4)
            message(jsondata)

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

            logging.debug(f"Getting landmarks of {path}")

            if not args.output:
                outpath = None
            else:
                out = Path(args.output)

                if out.is_dir():
                    outpath = f"{out}/{Path(path).name}"
                else:
                    outpath = str(out)

            marks = landmarks.get_landmarks(str(path), outpath = outpath)

            if marks and save_data:
                points = [str(path)]
                [points.extend([m.x, m.y]) for m in marks]
                data.append(points)

            message(path, marks)

        if save_data:
            df = pd.DataFrame(data)

            if args.output_format == "csv":
                df.to_csv(args.output)
            elif args.output_format == "json":
                df.to_json(args.output)
            else:
                raise ArgumentError(f"Invalid output format: {args.output_format}")

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

            poses = poser.get_poses(path, outpath = outpath)

            message(f"{path}: {poses}")

    elif args.command == "count":
        from facetool.detect import Detect

        detect = Detect()

        if args.output_format == "csv":
            csv = []

        for path in Path(args.input).images():
            count = detect.count(path)

            message(f"Number of faces in '{path}': {count}")

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
            message(f"Face locations in '{args.input}': {locations}")

    elif args.command == "crop":
        from facetool.detect import Detect
        from facetool.media import extractframes

        # We can't crop to an image path, because an input image might
        # have multiple faces, so throw an error in that case
        if Path(args.output).is_image():
            raise ArgumentError(f"Can't crop with an image as output")

        detect = Detect()

        # FIXME: we need some general mechanism for juggling frames around
        TMP_DIR = "crop-tmp"
        IS_VIDEO = Path(args.input).is_video()

        logging.debug(f"Cropping. Input is video? {IS_VIDEO}")

        if IS_VIDEO:
            force_mkdir(TMP_DIR)
            extractframes(args.input, TMP_DIR)
            images = Path(TMP_DIR).images()
        else:
            images = Path(args.input).images()

        for path in images:
            logging.debug(f"Cropping <{path}>")
            detect.crop(str(path), args.output)

        if IS_VIDEO:
            shutil.rmtree(TMP_DIR)

    elif args.command == "classify":
        from facetool.classifier import Classifier

        classifier = Classifier(
            data_directory = args.data_directory,
            output_format = args.output_format,
            predictor_path = args.predictor_path
        )

        for path in Path(args.input).images():
            logging.debug(f"Classifying <{path}>")
            classifier.classify(str(path))

        if args.output_format == "csv":
            classifier.to_csv(args.output)

    elif args.command == "average":
        from facetool.averager import Averager

        profiler.tick("start averaging")

        averager = Averager(
            predictor_path = args.predictor_path,
            img_height = args.image_height,
            img_width = args.image_width,
            save_originals = args.save_originals,
            save_warped = args.save_warped
        )

        TMP_DIR = "average-tmp"
        path = Path(args.input)

        # If this is a video, extract all images and average those
        if path.is_file() and path.is_video():
            # First create a temporary directory to hold all frames
            util.mkdir_if_not_exists(TMP_DIR)
            media.extractframes(args.input, TMP_DIR)

            # Now average
            averager.average(TMP_DIR, args.output)

            # And remove the temporary directory
            logging.debug(f"Removing {TMP_DIR}")
            shutil.rmtree(TMP_DIR)
        # Not a video, so if it's a file it's probably an image
        # extract all faces and average those
        elif path.is_file():
            # First create a temporary directory
            util.mkdir_if_not_exists(TMP_DIR)

            # Now extract all the images to said directory
            from facetool.detect import Detect

            detect = Detect()

            logging.debug(f"Cropping <{args.input}> to {TMP_DIR}")
            detect.crop(str(args.input), TMP_DIR)

            # Average the stuff
            averager.average(TMP_DIR, args.output)

            # And remove the temporary directory
            logging.debug(f"Removing {TMP_DIR}")
            shutil.rmtree(TMP_DIR)
        elif path.is_dir():
            # Just a directory, use this
            averager.average(args.input, args.output)
        else:
            raise ArgumentError("Invalid input for averaging")

        profiler.tick("done averaging")

    elif args.command == "distance":
        from facetool.recognizer import Recognizer

        if not all([args.input, any([args.target, args.model])]):
            raise ArgumentError("For the recognizer you need an input and target/model")

        logging.debug(f"Trying to recognize {args.input} in {args.target}{args.model}")

        recognizer = Recognizer()

        results = recognizer.recognize(
            input_path = args.input,
            model_path = args.model,
            target_path = args.target,
            as_percentage = args.as_percentage
        )

        if args.output_format == "csv":
            pd.Series(results).to_csv(args.output, header = False)
        elif args.output_format == "json":
            pd.Series(results).to_json(args.output)
        else:
            message(f"{args.input} distance to {args.target}")
            for path, distance in results.items():
                message(f"{path}: {distance}")

    elif args.command == "encode":
        from facetool.recognizer import Recognizer

        if not all([args.input, args.output]):
            raise ArgumentError("For encoding faces you need both input and output")

        recognizer = Recognizer()
        encodings = recognizer.encode_path(args.input)

        with open(args.output, "w") as f:
            f.write(encodings)

        message(f"Written encodings of {args.input} to {args.output}")

    elif args.command == "cluster":
        from facetool.clusterer import Clusterer

        # A .json file with encodings is also valid, if that is give, use that
        # instead
        if is_json_path(args.input):
            encodings = Knead(args.input).data()["encodings"]
        else:
            from facetool.recognizer import Recognizer
            recognizer = Recognizer()
            encodings = recognizer.encode_path(args.input, return_type = "dict")
            encodings = encodings["encodings"]

        clusterer = Clusterer()
        output = clusterer.cluster_encodings(encodings)

        if args.output:
            if is_json_path(args.output):
                Knead(output).write(args.output)
            else:
                force_mkdir(args.output)
                clusterer.move_files(output, args.output)
        else:
            # Just print the output
            Knead(output).print()

    elif args.command == "swap":
        from facetool.swapper import Swapper

        profiler.tick("start swapping")
        # First check if all arguments are given
        arguments = [args.input, args.target]

        if not all(arguments + [args.output]):
            raise ArgumentError("Input, target and output are required for swapping")

        # And if these things are paths or files
        if not all([os.path.exists(a) for a in arguments]):
            raise ArgumentError("Input and target should be valid files or directories")

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
            keep_temp = args.keep_temp,
            swap_audio = not args.no_audio,
            overlay_eyesbrows = not args.no_eyesbrows,
            overlay_nosemouth = not args.no_nosemouth,
            only_mouth = args.only_mouth,
            reporthook = update_pbar,
            swap_method = args.swap_method,
            warp_3d = args.warp_3d,
            swap_order = args.swap_order,
            swap_order_repeat = args.swap_order_repeat,
            ignore_nofaces = args.ignore_nofaces,
            concurrent = not args.no_threading,
            colour_correct = not args.no_colour_correct,
            temp_dir = args.temp_dir
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
            raise ArgumentError("Invalid swap options")

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
    except IsADirectoryError as e:
        print(f"Can't use a directory as an argument: {e}")

    if config.PROFILE:
        profiler.dump_events()
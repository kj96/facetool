# facetool.py
> Command line utility to manipulate and detect faces in videos and images, written in Python 3

This library and command line tool is mostly a wrapper around well-known libraries and algorithms like `ffmpeg`, `dlib`, `opencv` and `face_recognition`.

## Installation
You'll need `git` and [`pipenv`](https://pipenv.readthedocs.io/en/latest/install/#installing-pipenv). Obviously, you also need a working installation of Python 3. I recommend the [Anaconda](https://www.anaconda.com/download) distribution. If you're on macOS this will all be much easier if you first install [`brew`](https://brew.sh/).

1. Clone this repository: `git clone https://github.com/hay/facetool.git`
2. Run `pipenv install`. This might take a while!
3. Run `pipenv shell`
4. Try running the script by typing `./facetool.py`

If that all works you can try some of the commands below.

## Features

### Face swapping on images and video files

Put the features of face.jpg on head.jpg and save the result as swap.jpg

    facetool.py swap -i face.jpg -t head.jpg -o swap.jpg

Put the features of face.jpg on a video file called head.mp4 and save as swap.mp4

    facetool.py swap -i face.jpg -t head.mp4 -o swap.mp4

Put the features of a video file called face.mp4 on another video file called head.mp4 and save as swap.mp4

    facetool.py swap -i face.mp4 -t head.mp4 -o swap.mp4

Take one 'head' image called `head.jpg` and generate a new faceswap for every file in a directory called `dir-to-face`.

    facetool.py swap -i faces -t head.jpg -o dir-to-face

The other way around: apply the face of `face.jpg` to a directory of `heads` and output to a directory called `face-to-dir`

    facetool.py swap -i face.jpg -t heads -o face-to-dir

### Face detection, position and cropping

Count the number of faces in `face.jpg`

    facetool.py count -i face.jpg

Count the number of faces in all images in directory `faces`

    facetool.py count -i faces

Show the bounding box of all faces in `face.jpg`

    facetool.py locate -i face.jpg

Create a new image called `face-box.jpg` that draws bounding boxes around all faces in `face.jpg`

    facetool.py locate -i face.jpg -o face.box.jpg

Draw bounding boxes on all faces for all images in directory `faces` and save to `locations`

    facetool.py locate -i faces -o locations

Show the poses of all faces in `face.jpg`

    facetool.py pose -i face.jpg

Create a new image called `face-pose.jpg` that shows the shapes and poses of `face.jpg`

    facetool.py pose -i face.jpg -o face-pose.jpg

Crop all faces from `face.jpg` and save to new files in the directory `cropped`

    facetool.py crop -i face.jpg -o cropped

### Media utilites
Convert a movie file called `movie.mp4` to a set of JPG files in a directory called `frames` (used for video swapping)

    facetool.py extractframes -i movie.mp4 -o frames

Convert a set of JPG files from the directory `frames` to a movie file called `movie.mp4` (used for video swapping)

    facetool.py combineframes -i frames -o movie.mp4

Return metadata about an image or video file in JSON format

    facetool.py probe -i movie.mp4

## All options

```bash
usage: facetool.py [-h] -i INPUT [-o OUTPUT] [-t TARGET] [-bl BLUR]
                   [-fr FRAMERATE] [-fa FEATHER] [-kt] [-pp PREDICTOR_PATH]
                   [-s] [-v] [-vv]
                   [{combineframes,count,crop,extractframes,locate,poseprobe,swap}]

Manipulate faces in videos and images

positional arguments:
  {combineframes,count,crop,extractframes,locate,poseprobe,swap}

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input file or folder, 'face' when swapping
  -o OUTPUT, --output OUTPUT
                        Output file or folder
  -t TARGET, --target TARGET
                        'Head' when swapping
  -bl BLUR, --blur BLUR
                        Amount of blur to use during colour correction
  -fr FRAMERATE, --framerate FRAMERATE
  -fa FEATHER, --feather FEATHER
                        Softness of edges on a swapped face
  -kt, --keep-temp      Keep temporary files (used with video swapping
  -pp PREDICTOR_PATH, --predictor-path PREDICTOR_PATH
  -s, --swap            Swap input and target
  -v, --verbose         Show debug information
  -vv, --extra-verbose  Show debug information AND raise / abort on exceptions
```

## Credits
Written by [Hay Kranen](https://www.haykranen.nl).

### Faceswapping
Faceswapping algorithm by [Matthew Earl](http://matthewearl.github.io/2015/07/28/switching-eds-with-python/), licensed under the MIT license.

Copyright (c) 2015 Matthew Earl

## License
Licensed under the [MIT license](https://opensource.org/licenses/MIT).
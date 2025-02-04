# Image Summaries

Guild supports ephemeral image summaries when viewing runs in
TensorBoard.

1. A run generates one or more images.

2. While running, Guild TensorBoard scans run dirs for generated images
   and includs them in an ephemeral summary log so they appear in
   TensorBoard for the applicable run.

To illustrate we use the `image-summaries` project.

    >>> project = Project(sample("projects", "image-summaries"))

The `copy-images` operation makes a copy of project-defined images.

    >>> run, _out = project.run_capture("copy-images")

Here are the run files:

    >>> files = dir(run.dir)
    >>> files
    ['.guild', 'copy_images.py', 'favicon-copy.png', 'favicon.png',
     'guild.yml', 'heart-copy.jpg', 'heart.jpg', 'rotate_images.py']

Next we process these files using the TensorBoard runs monitor. This
monitor checks runs for images and adds them to ephemeral summary logs
in a log directory.

    >>> from guild.tensorboard import RunsMonitor

Let's create a log directory. This is where the monitor stores run
summary logs.

    >>> logdir = mkdtemp()

The monitor needs a callback for listing runs. We use the project.

    >>> list_runs_cb = project.list_runs

Our monitor, configured to log only images:

    >>> monitor = RunsMonitor(logdir, list_runs_cb, log_hparams=False)

The monitor is designed to run a thread but we can run it preemptively
by calling `run_once`.

    >>> monitor.run_once()

The monitor generates the following files in the log directory:

    >>> files = findl(logdir)
    >>> len(files)
    8

    >>> pprint(files)
    ['... copy-images ... '
     '.../.images/events.out.tfevents.0000000000.image.71a365d27894b323b8d5d6ebfeed6ee9',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000001.image.f50c73d00fda2bd6d78ce4082e70f008',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000002.image.6eba6ff0fe3882f00774e289ff61c3e2',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000003.image.1ba04541731568ec8cb997f80fa0d246',
     '... copy-images .../favicon-copy.png',
     '... copy-images .../favicon.png',
     '... copy-images .../heart-copy.jpg',
     '... copy-images .../heart.jpg']

The TensorBoard runs monitor mirrors the run directory structure by
creating the appropriate symlinks to run files. This ensures that
TensorBoard plugins have full access to run files.

The monitor also generates Guild specific TF event files for each
image it finds. Each event file is named using an incrementing
timestamp starting with 0 and a digest suffix. The digest corresponds
to the logged image path, relative to the run directory.

Let's confirm each of the suffixes.

For `favicon-copy.png`:

    >>> import hashlib
    >>> digest0 = hashlib.md5(b"favicon-copy.png").hexdigest()

    >>> print(digest0)
    71a365d27894b323b8d5d6ebfeed6ee9

    >>> digest0 == files[0][-32:], (digest0, files[0])
    (True, ...)

For `heart-copy.jpg`:

    >>> digest1 = hashlib.md5(b"heart-copy.jpg").hexdigest()

    >>> print(digest1)
    6eba6ff0fe3882f00774e289ff61c3e2

    >>> digest1 == files[2][-32:], (digest1, files[2])
    (True, ...)

We can use `tfevent.EventReader` to read the log events.

    >>> from guild import tensorboard

    >>> tensorboard.setup_logging()

    >>> from guild.tfevent import EventReader
    >>> for event in EventReader(path(logdir, dirname(files[0]))):
    ...     print(event)
    summary {
      value {
        tag: "favicon-copy.png"
        image {
          height: 180
          width: 180
          colorspace: 4
          encoded_image_string: "..."
        }
      }
    }
    <BLANKLINE>
    summary {
      value {
        tag: "heart-copy.jpg"
        image {
          height: 50
          width: 50
          colorspace: 3
          encoded_image_string: ..."
        }
      }
    }

The monitor supports updates to images. When an image is modified, the
monitor creates a new summary with the latest image. This is generated
as a new tfevent file with the same path digest extension.

Let's demonstrate by modifying the timestamp of one of our images.

    >>> touch(path(run.dir, "favicon-copy.png"))

And re-run the monitor:

    >>> monitor.run_once()

The log directory now contains an additional file.

    >>> files = findl(logdir)
    >>> len(files)
    9

    >>> pprint(files)
    ['... copy-images ... '
     '.../.images/events.out.tfevents.0000000000.image.71a365d27894b323b8d5d6ebfeed6ee9',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000001.image.f50c73d00fda2bd6d78ce4082e70f008',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000002.image.6eba6ff0fe3882f00774e289ff61c3e2',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000003.image.1ba04541731568ec8cb997f80fa0d246',
     '... copy-images ... '
     '.../.images/events.out.tfevents.0000000004.image.71a365d27894b323b8d5d6ebfeed6ee9',
     '... copy-images .../favicon-copy.png',
     '... copy-images .../favicon.png',
     '... copy-images .../heart-copy.jpg',
     '... copy-images .../heart.jpg']

And has a second image summary for `favicon-copy.png`:

    >>> for event in EventReader(path(logdir, dirname(files[0]))):
    ...     print(event)
    summary {
      value {
        tag: "favicon-copy.png"
        image {
          height: 180
          width: 180
          colorspace: 4
          encoded_image_string: "..."
        }
      }
    }
    <BLANKLINE>
    summary {
      value {
        tag: "heart-copy.jpg"
        image {
          height: 50
          width: 50
          colorspace: 3
          encoded_image_string: ..."
        }
      }
    }
    <BLANKLINE>
    summary {
      value {
        tag: "favicon-copy.png"
        image {
          height: 180
          width: 180
          colorspace: 4
          encoded_image_string: "..."
        }
      }
    }

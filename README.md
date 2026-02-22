# himena-relion

[![PyPI - Version](https://img.shields.io/pypi/v/himena-relion.svg)](https://pypi.org/project/himena-relion)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/himena-relion.svg)](https://pypi.org/project/himena-relion)
[![codecov](https://codecov.io/gh/hanjinliu/himena-relion/graph/badge.svg?token=7BS2gF92SL)](https://codecov.io/gh/hanjinliu/himena-relion)

-----

`himena-relion` is a modern RELION GUI implemented as a [himena](https://github.com/hanjinliu/himena) plugin.

(Original dataset is from [RELION STA tutorial](https://relion.readthedocs.io/en/latest/SPA_tutorial/Introduction.html))

![](docs/images/main.png)

#### [&rarr; Documentation](https://hanjinliu.github.io/himena-relion/)

## Installation

```bash
pip install himena-relion[recommended]  # install packages
```

`himena-relion` is a plugin of [himena](https://github.com/hanjinliu/himena) plugin. You will need to install both packages into the same Python environment, and mark `himena-relion` as a startup plugin of your himena profile. For more details, please refer to the [installation guide](https://hanjinliu.github.io/himena-relion/installation/).


## Highlights

#### View, queue and run RELION single-particle and tomography jobs

Outputs of most of the job types can be directly visualized in the GUI.

#### Efficient 2D/3D rendering over SSH using [vispy](https://github.com/vispy/vispy) and EGL

`himena-relion` is not a web-based application &mdash; this has a huge advantage in the interactive rendering of large images that is essential especially for cryo-ET. Owing to the powerful [`vispy`](https://github.com/vispy/vispy) backend and EGL offscreen rendering, `himena-relion` can provide efficient 2D/3D rendering even over SSH.

#### View and open jobs from the flowchart

You can interactively view your RELION job pipeline as a flowchart, open jobs and its input/output files.

#### RELION "external" jobs

You can safely create a RELION external job by subclassing `RelionExternalJob`.
`himena-relion` also provides useful external jobs missing in the RELION GUI, such as
"Erase Golds" and "Shift Map".

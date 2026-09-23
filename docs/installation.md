# Installation

## 1. Install RELION

Currently `himena-relion` only supports RELION 5.x.x. Please follow the instructions in
the [RELION documentation](https://relion.readthedocs.io/en/latest/Installation.html).

## 2. Create a Python environment

Installation in a Python virtual environment is recommended to avoid conflicts with
other packages. For example, you can use [miniforge](https://github.com/conda-forge/miniforge) to create a minimum conda environment in your user directory.

## 3. Install `himena-relion`

Activate the Python environment you created in the previous step, and then run the following command to install `himena-relion`:

```bash
pip install himena-relion[recommended]
```

## 4. Make `himena relion` command

You can create a "profile" for use of `himena` as a RELION GUI. Practically, if you name
your profile `relion`, you will register `himena relion` subcommand as a shortcut to
launch the RELION GUI.

Following lines will create a `relion` profile and activate `himena-relion` plugin in
the profile.

```bash
himena --new relion  # create a new profile named "relion"
himena relion --install himena-relion  # install the plugin into "relion" profile
```

Now, you can launch the RELION GUI.

```bash
himena relion
himena relion &  # launch the GUI in the background
```

!!! note title="Running RELION in WSL from native Windows"

    :sparkles: *New in v0.0.13*

    If you have RELION and `himena-relion` installed in WSL, of course you can start
    by running `himena relion` in WSL. On top of that, `himena-relion` also has an
    experimental feature to launch the RELION GUI from the Windows side. This allows
    you to interact with the RELION jobs as if it were running natively on Windows
    (which usually provides better user experience), while the actual computation is
    performed in WSL.

    To do this, you need to set up `himena-relion` as shown above in both WSL and
    Windows environments. On the Windows side, you can open a "default_pipeline.star"
    file saved in WSL using the native file dialog, or directly writing the path
    starting with "\\wsl". `himena-relion` GUI will automatically detect the WSL
    environment.

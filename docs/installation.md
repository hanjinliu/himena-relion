# Installation

## 1. Install RELION

Currently `himena-relion` only supports RELION 5.0. Please follow the instructions in
the [RELION documentation](https://relion.readthedocs.io/en/latest/Installation.html).

## 2. Create a Python environment

Installation in a Python virtual environment is recommended to avoid conflicts with other packages. For example, you can use [miniforge](https://github.com/conda-forge/miniforge) to create a minimum conda environment in your user directory.

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

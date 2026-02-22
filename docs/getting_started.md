# Getting Started

```bash
himena relion
```

## Configuration

Before starting your image processing, you need to configure the paths to executables
and scripts that RELION jobs will call.

Open the himena setting dialog (++ctrl+comma++) and select the "Configurations" tab.
Type "relion" in the search bar, and you will see the configuration items related to
RELION as shown below.

![](images/00_config.png){ width=600px loading=lazy }

These values will be automatically used for the RELION jobs that take these executables
or scripts as input.

## Launch Existing RELION Project

`himena-relion` and RELION GUI is compatible. If you have an existing RELION project,
just run `himena relion` under the project directory

```bash
cd path/to/my-project
himena relion &
```

or pass the project path as an argument

```bash
himena relion path/to/my-project &
```

You can also open a RELION project by:

- ++ctrl+o++ and select the default_pipeline.star file.
- from the "Recent Files" in the startup window.
- from the recent-file command palette (++ctrl+k++ &rarr; ++ctrl+r++)

## Create New RELION Project

If RELION project is not initialized in the current directory yet, you'll have to create
one. You can do this by opening the command palette (++ctrl+shift+p++) and running the "Start New RELION Project" command.

![](images/01_new_cmd_palette.png){ width=400px loading=lazy }

Once the default_pipeline.star file is created, you'll see a dock widget on the left.
You can click any of the import jobs to start processing your data.

![](images/01_flowchart_startup.png){ width=400px loading=lazy }

## Job Flowchart

## Job Window

## Use Action Hint!

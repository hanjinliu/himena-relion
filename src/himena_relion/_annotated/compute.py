from typing import Annotated


USE_PARALLEL_DISC_IO = Annotated[
    bool,
    {
        "label": "Use parallel disc I/O",
        "tooltip": (
            "If set to Yes, all MPI followers will read their own images from disc. "
            "Otherwise, only the leader will read images and send them through the "
            "network to the followers. Parallel file systems like gluster of fhgfs are "
            "good at parallel disc I/O. NFS may break with many followers reading in "
            "parallel. If your datasets contain particles with different box sizes, "
            "you have to say Yes."
        ),
        "group": "Compute",
    },
]
NUM_POOL = Annotated[
    int,
    {
        "label": "Number of pooled particles",
        "tooltip": (
            "Particles are processed in individual batches by MPI followers. During "
            "each batch, a stack of particle images is only opened and closed once to "
            "improve disk access times. All particle images of a single batch are read "
            "into memory together. The size of these batches is at least one particle "
            "per thread used. The nr_pooled_particles parameter controls how many "
            "particles are read together for each thread. If it is set to 3 and one "
            "uses 8 threads, batches of 3x8=24 particles will be read together. This "
            "may improve performance on systems where disk access, and particularly "
            "metadata handling of disk access, is a problem. It has a modest cost of "
            "increased RAM usage."
        ),
        "min": 1,
        "group": "Compute",
    },
]
DO_PREREAD = Annotated[
    bool,
    {
        "label": "Pre-read all particles into RAM",
        "tooltip": (
            "If set to Yes, all particle images will be read into computer memory, "
            "which will greatly speed up calculations on systems with slow disk "
            "access. However, one should of course be careful with the amount of RAM "
            "available. Because particles are read in float-precision, it will take "
            "( N * box_size * box_size * 4 / (1024 * 1024 * 1024) ) Giga-bytes to "
            "read N particles into RAM. For 100 thousand 200x200 images, that "
            "becomes 15Gb, or 60 Gb for the same number of 400x400 particles. "
            "Remember that running a single MPI follower on each node that runs as "
            "many threads as available cores will have access to all available RAM.\n\n"
            "If parallel disc I/O is set to No, then only the leader reads all "
            "particles into RAM and sends those particles through the network to the "
            "MPI followers during the refinement iterations."
        ),
        "group": "Compute",
    },
]
USE_SCRATCH = Annotated[
    bool,
    {
        "label": "Copy particles to scratch directory",
        "tooltip": (
            "Preload particles to scratch directory to improve I/O performance during "
            "computation.",
        ),
        "group": "Compute",
    },
]
DO_COMBINE_THRU_DISC = Annotated[
    bool,
    {
        "label": "Combine iterations through disc",
        "tooltip": (
            "If set to Yes, at the end of every iteration all MPI followers will "
            "write out a large file with their accumulated results. The MPI leader "
            "will read in all these files, combine them all, and write out a new file "
            "with the combined results. All MPI salves will then read in the combined "
            "results. This reduces heavy load on the network, but increases load on "
            "the disc I/O. This will affect the time it takes between the "
            "progress-bar in the expectation step reaching its end (the mouse gets to "
            "the cheese) and the start of the ensuing maximisation step. It will "
            "depend on your system setup which is most efficient."
        ),
        "group": "Compute",
    },
]
DO_PAD1 = Annotated[
    bool,
    {
        "label": "Skip padding",
        "tooltip": (
            "If set to Yes, the calculations will not use padding in Fourier space "
            "for better interpolation in the references. Otherwise, references are "
            "padded 2x before Fourier transforms are calculated. Skipping padding "
            "(i.e. use --pad 1) gives nearly as good results as using --pad 2, but "
            "some artifacts may appear in the corners from signal that is folded back."
        ),
        "group": "Compute",
    },
]
GPU_IDS = Annotated[
    str,
    {
        "label": "GPU IDs to use",
        "tooltip": (
            "Provide a list of which GPUs (0,1,2,3, etc) to use. MPI-processes are "
            "separated by ':'. For example, to place one rank on device 0 and one "
            "rank on device 1, provide '0:1'.\nNote that multiple MotionCor2 "
            "processes should not share a GPU; otherwise, it can lead to crash or "
            "broken outputs (e.g. black images) ."
        ),
        "group": "Compute",
    },
]
USE_FAST_SUBSET = Annotated[
    bool,
    {
        "label": "Use fast subsets",
        "tooltip": (
            "If set to Yes, the first 5 iterations will be done with random subsets "
            "of only K*1500 particles (K being the number of classes); the next 5 "
            "with K*4500 particles, the next 5 with 30% of the data set; and the "
            "final ones with all data. This was inspired by a cisTEM implementation "
            "by Niko Grigorieff et al."
        ),
        "group": "Compute",
    },
]

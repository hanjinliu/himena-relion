
# version 50001   2D stacks

data_job

_rlnJobTypeLabel             relion.pseudosubtomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
   binning          1
  box_size        128
 crop_size         -1
do_float16        Yes
  do_queue         No
do_stack2d        Yes
in_optimisation          ****
in_particles         ""
in_tomograms         ""
in_trajectories         ""
  max_dose         -1
min_dedicated          1
min_frames          1
    nr_mpi          1
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
use_direct_entries         No


# version 50001

data_job

_rlnJobTypeLabel             relion.ctfrefinetomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
  box_size        128
do_defocus        Yes
do_frame_scale        Yes
  do_queue         No
do_reg_def         No
  do_scale        Yes
do_tomo_scale         No
focus_range       3000
in_halfmaps    f_half1
in_optimisation   Extract/job010/optimisation_set.star
in_particles         ""
   in_post         ""
in_refmask         ""
in_tomograms         ""
in_trajectories         ""
    lambda        0.1
min_dedicated          1
    nr_mpi          1
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
use_direct_entries         No

# version 50001

data_job

_rlnJobTypeLabel             relion.framealigntomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
  box_size        128
 do_motion         No
  do_queue         No
do_shift_align        Yes
do_sq_exp_ker         No
in_halfmaps Reconstruct/job060/half1.mrc
in_optimisation Reconstruct/job060/optimisation_set.star
in_particles         ""
   in_post PostProcess/job061/postprocess.star
in_refmask MaskCreate/job054/mask.mrc
in_tomograms         ""
in_trajectories         ""
 max_error          5
min_dedicated          1
    nr_mpi          1
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
shift_align_type "Entire micrographs"
 sigma_div       5000
 sigma_vel        0.2
use_direct_entries         No

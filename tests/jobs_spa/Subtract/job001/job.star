# version 50001

data_job

_rlnJobTypeLabel             relion.subtract
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
  center_x        0.0
  center_y        0.0
  center_z        0.0
do_center_mask        Yes
do_center_xyz         No
   do_data         No
do_fliplabel         No
do_float16        Yes
  do_queue         No
   fn_data         ""
fn_fliplabel         ""
   fn_mask External/job100/mask.mrc
    fn_opt Refine3D/job050/run_optimiser.star
min_dedicated          1
   new_box         -1
    nr_mpi          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi

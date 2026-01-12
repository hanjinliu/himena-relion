# version 50001

data_job

_rlnJobTypeLabel             dynamight
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
backproject_batchsize         10
do_inverse         No
do_preload         No
  do_queue         No
do_reconstruct         No
do_store_deform         No
do_visualize         No
fn_checkpoint         ""
fn_dynamight_exe relion_python_dynamight
    fn_map   *ref.mrc
   fn_star *image.star
    gpu_id          0
   halfset          1
initial_threshold         ""
min_dedicated          1
 nr_epochs        200
nr_gaussians      10000
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
reg_factor          1

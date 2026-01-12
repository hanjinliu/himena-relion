# version 50001

data_job

_rlnJobTypeLabel             relion.polish
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
do_float16        Yes
do_own_params        Yes
do_param_optim         No
 do_polish        Yes
  do_queue         No
 eval_frac        0.5
extract_size         -1
first_frame          1
   fn_data run_data.star
    fn_mic micrographs.star
   fn_post postprocess.star
last_frame         -1
    maxres         -1
min_dedicated          1
    minres         20
    nr_mpi          1
nr_threads          1
opt_params         ""
optim_min_part      10000
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
   rescale         -1
 sigma_acc          2
 sigma_div       5000
 sigma_vel        0.2

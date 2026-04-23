# version 50001

data_job

_rlnJobTypeLabel             relion.multibody
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
do_analyse        Yes
  do_blush         No
do_combine_thru_disc         No
   do_pad1         No
do_parallel_discio        Yes
do_preread_images         No
  do_queue         No
 do_select         No
do_subtracted_bodies        Yes
eigenval_max        999
eigenval_min       -999
 fn_bodies body.star
   fn_cont         ""
     fn_in consensus.star
   gpu_ids         ""
min_dedicated          1
 nr_movies          3
    nr_mpi          1
   nr_pool          3
nr_threads          1
offset_range          3
offset_step       0.75
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
  sampling "1.8 degrees"
scratch_dir         ""
select_eigenval          1
   use_gpu         No

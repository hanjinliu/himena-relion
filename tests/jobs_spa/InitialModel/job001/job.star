# version 50001

data_job

_rlnJobTypeLabel             relion.initialmodel
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
ctf_intact_first_peak         No
do_combine_thru_disc         No
do_ctf_correction        Yes
do_parallel_discio        Yes
do_preread_images         No
  do_queue         No
 do_run_C1        Yes
do_solvent        Yes
   fn_cont         ""
    fn_img Select/job009/particles.star
   gpu_ids         ""
min_dedicated          1
nr_classes          1
   nr_iter        200
    nr_mpi          1
   nr_pool          3
nr_threads          1
other_args         ""
particle_diameter        200
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
scratch_dir         ""
  sym_name         C1
 tau_fudge          4
   use_gpu         No

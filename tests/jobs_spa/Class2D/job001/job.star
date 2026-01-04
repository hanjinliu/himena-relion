# version 50001

data_job

_rlnJobTypeLabel             relion.class2d
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
allow_coarser         No
ctf_intact_first_peak         No
do_bimodal_psi        Yes
 do_center        Yes
do_combine_thru_disc         No
do_ctf_correction        Yes
     do_em         No
   do_grad        Yes
  do_helix         No
do_parallel_discio        Yes
do_preread_images         No
  do_queue         No
do_restrict_xoff        Yes
do_zero_mask        Yes
dont_skip_align        Yes
   fn_cont         ""
    fn_img Extract/job123/particles.star
   gpu_ids         ""
helical_rise       4.75
helical_tube_outer_diameter        200
highres_limit         -1
min_dedicated          1
nr_classes          1
nr_iter_em         25
nr_iter_grad        200
    nr_mpi          1
   nr_pool          3
nr_threads          1
offset_range          5
offset_step          1
other_args         ""
particle_diameter        200
psi_sampling          6
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
 range_psi          6
scratch_dir         ""
 tau_fudge          2
   use_gpu         No

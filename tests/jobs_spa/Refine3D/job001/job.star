# version 50001

data_job

_rlnJobTypeLabel             relion.refine3d
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
auto_faster         No
auto_local_sampling "1.8 degrees"
ctf_intact_first_peak         No
do_apply_helical_symmetry        Yes
  do_blush         No
do_combine_thru_disc         No
do_ctf_correction        Yes
  do_helix         No
do_local_search_helical_symmetry         No
   do_pad1         No
do_parallel_discio        Yes
do_preread_images         No
  do_queue         No
do_solvent_fsc         No
do_zero_mask        Yes
   fn_cont         ""
    fn_img Refine3D/job014/run_it019_optimiser.star
   fn_mask Extract/job013/particles.star
    fn_ref Class3D/job011/run_it015_class003.mrc
   gpu_ids         0
helical_nr_asu          1
helical_range_distance         -1
helical_rise_inistep          0
helical_rise_initial          0
helical_rise_max          0
helical_rise_min          0
helical_tube_inner_diameter         -1
helical_tube_outer_diameter         -1
helical_twist_inistep          0
helical_twist_initial          0
helical_twist_max          0
helical_twist_min          0
helical_z_percentage         30
  ini_high         60
keep_tilt_prior_fixed        Yes
min_dedicated          1
    nr_mpi          1
   nr_pool          3
nr_threads          1
offset_range          5
offset_step          1
other_args         ""
particle_diameter        200
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
 range_psi         10
 range_rot         -1
range_tilt         15
ref_correct_greyscale         No
 relax_sym         ""
  sampling "7.5 degrees"
scratch_dir         ""
  sym_name         C1
trust_ref_size        Yes
   use_gpu         No

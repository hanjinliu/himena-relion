# version 50001

data_job

_rlnJobTypeLabel             relion.extract.reextract
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
bg_diameter         -1
black_dust         -1
coords_suffix *coords.star
do_cut_into_segments        Yes
do_extract_helical_tubes        Yes
do_extract_helix         No
do_float16        Yes
do_fom_threshold         No
 do_invert        Yes
   do_norm        Yes
  do_queue         No
do_recenter         No
do_reextract        Yes
do_rescale        Yes
do_reset_offsets        Yes
extract_size        128
fndata_reextract Refine3D/job001/run_data.star
helical_bimodal_angular_priors        Yes
helical_nr_asu          1
helical_rise          1
helical_tube_outer_diameter        200
min_dedicated          1
minimum_pick_fom          0
    nr_mpi          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
recenter_x          0
recenter_y          0
recenter_z          0
   rescale        128
 star_mics CtfFind/job003/micrographs_ctf.star
white_dust         -1

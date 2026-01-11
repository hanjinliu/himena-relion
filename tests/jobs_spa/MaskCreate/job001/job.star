
# version 50001

data_job

_rlnJobTypeLabel             relion.maskcreate
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
    angpix         -1
  do_helix         No
  do_queue         No
extend_inimask          3
     fn_in          Refine3D/job040/run_class001.mrc
helical_z_percentage         30
inimask_threshold       0.02
lowpass_filter         15
min_dedicated          1
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
width_mask_edge          3

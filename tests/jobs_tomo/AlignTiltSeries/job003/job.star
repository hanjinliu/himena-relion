
# version 50001

data_job

_rlnJobTypeLabel             relion.aligntiltseries
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
aretomo_tiltcorrect_angle        999
do_aretomo2        Yes
do_aretomo_ctf         No
do_aretomo_phaseshift         No
do_aretomo_tiltcorrect         No
do_imod_fiducials         No
do_imod_patchtrack         No
  do_queue         No
fiducial_diameter         10
fn_aretomo_exe /public/EM/AreTomo/AreTomo2/AreTomo2
fn_batchtomo_exe /public/EM/imod/IMOD/bin/batchruntomo
   gpu_ids         ""
in_tiltseries ExcludeTiltImages/job004/selected_tilt_series.star
min_dedicated          1
    nr_mpi          1
other_aretomo_args         ""
other_args         ""
patch_overlap         50
patch_size        100
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
tomogram_thickness        300

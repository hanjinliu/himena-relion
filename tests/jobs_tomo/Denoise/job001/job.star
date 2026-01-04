
# version 50001   train

data_job

_rlnJobTypeLabel             relion.denoisetomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
care_denoising_model         ""
cryocare_path /public/EM/cryoCARE
denoising_tomo_name         ""
do_cryocare_predict         No
do_cryocare_train        Yes
  do_queue         No
   gpu_ids          0
in_tomoset          ****
min_dedicated          1
  ntiles_x          2
  ntiles_y          2
  ntiles_z          2
number_training_subvolumes       1200
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
subvolume_dimensions         72
tomograms_for_training          ****

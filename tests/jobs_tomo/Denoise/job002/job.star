
# version 50001

data_job

_rlnJobTypeLabel             relion.denoisetomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
care_denoising_model Denoise/job007/denoising_model.tar.gz
cryocare_path /public/EM/cryoCARE
denoising_tomo_name         ""
do_cryocare_predict        Yes
do_cryocare_train         No
  do_queue         No
   gpu_ids          0
in_tomoset Tomograms/job006/tomograms.star
min_dedicated         24
  ntiles_x          2
  ntiles_y          2
  ntiles_z          2
number_training_subvolumes       1200
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion-slurm-gpu-4.0.csh
 queuename    openmpi
subvolume_dimensions         72
tomograms_for_training TS_01:TS_03:TS_43:TS_45:TS_54

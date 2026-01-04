# version 50001

data_job

_rlnJobTypeLabel             relion.manualpick
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
    angpix         -1
 black_val          0
blue_value          0
color_label rlnAutopickFigureOfMerit
  diameter        100
  do_color         No
do_fom_threshold         No
  do_queue         No
do_startend         No
do_topaz_denoise         No
  fn_color         ""
     fn_in *micrographs.star
  highpass         -1
   lowpass         20
  micscale        0.2
min_dedicated          1
minimum_pick_fom          0
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
 red_value          2
sigma_contrast          3
 white_val          0

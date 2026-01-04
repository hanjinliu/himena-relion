
# version 50001 import tomograms

data_job

_rlnJobTypeLabel             relion.importtomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
        Cs        2.7
        Q0        0.1
add_factor          0
    angpix      0.675
 do_coords         No
  do_queue         No
dose_is_per_movie_frame         No
 dose_rate          3
flip_tiltseries_hand        Yes
images_are_motion_corrected         No
 in_coords         ""
 is_center         No
        kV        300
mdoc_files mdoc/*.mdoc
min_dedicated          1
movie_files frames/*.mrc
  mtf_file         ""
optics_group_name         ""
other_args         ""
    prefix         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
remove_substring         ""
remove_substring2         ""
scale_factor          1
tilt_axis_angle         85

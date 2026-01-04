
# version 50001

data_job

_rlnJobTypeLabel             relion.joinstar.particles
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
    do_mic         No
    do_mov         No
   do_part        Yes
  do_queue         No
   fn_mic1         ""
   fn_mic2         ""
   fn_mic3         ""
   fn_mic4         ""
   fn_mov1         ""
   fn_mov2         ""
   fn_mov3         ""
   fn_mov4         ""
  fn_part1          ****
  fn_part2          ****
  fn_part3         ""
  fn_part4         ""
min_dedicated          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi

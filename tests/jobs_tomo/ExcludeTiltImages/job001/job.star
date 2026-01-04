
# version 50001

data_job

_rlnJobTypeLabel             relion.excludetilts
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
cache_size          5
  do_queue         No
in_tiltseries          ****
min_dedicated          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi

# version 50001

data_job

_rlnJobTypeLabel             relion.ctfrefine
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
do_4thorder         No
do_aniso_mag        No
  do_astig         No
do_bfactor         No
    do_ctf        Yes
do_defocus Per-micrograph
  do_phase         No
  do_queue         No
   do_tilt         No
do_trefoil         No
   fn_data Refine3D/job030/run_data.star
   fn_post Postprocess/job029/postprocess.star
min_dedicated          1
    minres         30
    nr_mpi          1
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi

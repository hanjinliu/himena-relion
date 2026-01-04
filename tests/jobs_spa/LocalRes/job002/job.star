# version 50001

data_job

_rlnJobTypeLabel             relion.localres.own
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
adhoc_bfac       -150
    angpix        1.2
  do_queue         No
do_relion_locres        Yes
do_resmap_locres         No
     fn_in abc-half1.mrc
   fn_mask MaskCreate/job001/mask.mrc
    fn_mtf         ""
 fn_resmap /public/EM/ResMap/ResMap-1.1.4-linux64
    maxres          0
min_dedicated          1
    minres          0
    nr_mpi          1
other_args         ""
      pval       0.05
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
   stepres          1

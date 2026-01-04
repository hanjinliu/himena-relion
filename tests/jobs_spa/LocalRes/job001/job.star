
# version 50001

data_job

_rlnJobTypeLabel             relion.localres.resmap
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
adhoc_bfac       -100
    angpix          1
  do_queue         No
do_relion_locres         No
do_resmap_locres        Yes
     fn_in    Refine3D/job001/run_class001_unfil_half1.mrc
   fn_mask    MaskCreate/job001/mask.mrc
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

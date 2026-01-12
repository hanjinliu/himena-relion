# version 50001

data_job

_rlnJobTypeLabel             modelangelo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
         E         10
        F1       0.02
        F2      0.001
        F3      1e-05
  alphabet      amino
     d_seq         ""
  do_hhmer         No
  do_queue         No
    fn_lib         ""
    fn_map      m.map
fn_modelangelo_exe relion_python_modelangelo
    gpu_id          0
min_dedicated          1
other_args         ""
     p_seq    a.fasta
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
     r_seq         ""

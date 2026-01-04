
# version 50001

data_job

_rlnJobTypeLabel             relion.reconstructparticletomo
_rlnJobIsContinue                       0
_rlnJobIsTomo                           0


# version 50001

data_joboptions_values

loop_
_rlnJobOptionVariable #1
_rlnJobOptionValue #2
   binning          1
  box_size        128
 crop_size         -1
  do_helix         No
  do_queue         No
helical_nr_asu          1
helical_rise       4.75
helical_tube_outer_diameter        200
helical_twist         -1
helical_z_percentage         20
in_optimisation          Extract/job025/optimisation_set.star
in_particles         ""
in_tomograms         ""
in_trajectories         ""
min_dedicated          1
    nr_mpi          1
nr_threads          1
other_args         ""
      qsub     sbatch
qsubscript /public/EM/RELION/relion/bin/relion_qsub.csh
 queuename    openmpi
       snr          0
  sym_name         C1
use_direct_entries         No

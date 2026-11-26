# Built-in External Jobs

## General-Purpose Jobs

#### Symmetry Expansion

This job uses `relion_particle_symmetry_expand` to create a new particle star file with expanded particles.

#### Helical Symmetry Expansion

This job uses `relion_particle_symmetry_expand` to create a new particle star file with
helical symmetry expanded particles.

#### Shift Map

This job uses the `relion_star_handler` and a custom-built function to create a shifted
particles, map and mask. If you make a 3D reconstruction using the shifted particles,
the resulting map will be similar to the shifted map.

Common usage of this job will be:

- Re-center particles to the region of interest after 3D classification.
- Re-center particles to the subunits after symmetry expansion.

## Tomography-specific Jobs

![](../images/02_external_tomo.png){ loading=lazy }

#### Find Beads 3D

This job uses the `findbeads3d` program from [IMOD](https://bio3d.colorado.edu/imod/) to
locate fiducial gold beads in tomograms. The output files are IMOD .mod files. You can
check the results in the job widget.

#### Erase Gold

This job uses the output of the "Find Beads 3D" job to erase the gold beads **in the
un-aligned tilt series**. Therefore, subsequent denoising and particle reconstruction
using output tilt series from this job will not be affected by the strong contrast of
the gold beads.

#### Inspect Particles

This job simply creates a "optimisation_set.star" file from the inputs. The main purpose
of this job will be to inspect the filtered particle file after any of the "Select"
jobs.

#### Auto-exclude Tilt Images

This job automatically excludes bad tilt images based on the dark pixel percentage,
defocus, total motion, and ice thickness value.

#### Select Tomograms

This job keeps only some of the tomograms in a `tomograms.star` file, such as the output
of a "Reconstruct tomograms" or "Denoise tomograms" job. While the job is running, the
job window shows the Z slices of the tomograms with check boxes. Check the tomograms to
keep (the Space key toggles the current tomogram) and click "Save selection". The job
then saves the checked tomograms as `tomograms_selected.star` and finishes.

To change the selection later, click "Continue selection" in the job window. The
continued job starts from the last selection.

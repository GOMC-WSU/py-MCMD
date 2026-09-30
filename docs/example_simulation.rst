Illustration: Water Insertion in a Protein Binding Pocket
=========================================================

Hybrid NAMD/GOMC sampling can be used to alternate molecular dynamics with
grand-canonical insertion and deletion moves. In this example, NAMD evolves
the protein and solvent configuration, then GOMC samples water occupancy in a
binding pocket.

This is a visualization, not a runnable tutorial: the repository does not
include a complete BPTI input set. Use :doc:`quick_start` for the supplied
GEMC calculation. For a protein calculation, prepare and validate the
inputs described in :doc:`generating_systems` and
:doc:`simulation_parameters_files`.
The video illustrates a BPTI binding-pocket calculation. Green protein and
water spheres are crystallographic coordinates; purple protein and red/white
water are simulation output.

.. raw:: html

   <video controls width="100%">
     <source src="_static/Hybrid_MC_MD_BPTI.mp4" type="video/mp4">
     Your browser does not support embedded video.
   </video>

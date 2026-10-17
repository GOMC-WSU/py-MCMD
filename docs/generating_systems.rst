Preparing Simulation Systems
============================

py-MCMD requires a consistent system description for NAMD and GOMC. Prepare
PSF, PDB, and force-field inputs, then run a short calculation in each engine
independently before using the files in a hybrid workflow.

Required consistency checks
---------------------------

* The PSF and PDB must describe the same atoms in the same order. Atom
  types and bonded interactions must have parameters in each engine's
  force-field files.
* The PDB must provide valid box information through ``CRYST1``, unless all
  needed box lengths are supplied with ``set_dims_box_0_list`` and
  ``set_dims_box_1_list``.
* Boxes must be orthogonal. py-MCMD accepts only 90-degree angles.
* Check support for every force-field term in the installed engine builds,
  including improper and Urey-Bradley terms. Do not delete terms solely
  to make an input file load; doing so changes the molecular model.
* For GCMC, residue names used in the chemical-potential/fugacity dictionary
  must exactly match the names used by GOMC.
* Compare engine energies for the same coordinates, box, and interaction
  settings, after converting units. Investigate unexplained differences
  before running a coupled calculation.

Small-molecule and fluid systems
--------------------------------

`MoSDeF <https://mosdef.org>`_ can generate compatible structures and force
fields for many molecular systems. The relevant components are
`mBuild <https://mbuild.mosdef.org/en/stable/>`_,
`foyer <https://foyer.mosdef.org/en/stable/>`_, and
`GMSO <https://gmso.mosdef.org/en/stable/>`_. The
`GOMC-MoSDeF repository <https://github.com/GOMC-WSU/GOMC-MoSDeF>`_ provides
worked examples.

Protein and multiresidue systems
--------------------------------

Use a preparation workflow that preserves the residue and topology definitions
required by both engines. VMD or another appropriate builder may be used. In
particular, inspect fixed bonds, fixed angles, and force-field terms before
starting a hybrid run. A successful NAMD input alone does not establish that a
GOMC input is compatible.

Place finished inputs under a calculation-specific directory and reference
them from the JSON file. Keep the initial inputs unchanged when restarting. See
:doc:`simulation_parameters_files` for the exact path fields.

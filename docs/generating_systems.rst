
Generating Systems
=======

Traditional Chemical Engineering Systems
-------

Traditional chemical engineering systems are not proteins or other molecules requiring multiple residue names per molecule.  For these systems, the `Molecular Simulation Design Framework (MoSDeF) <https://mosdef.org>`_ software is **capable of generating all the PSF, PDB, and force field files required for the GOMC and NAMD simulations**, covering a variety of different systems.  The **MoSDeF** software creates all these files using only tens of lines of Python code.
The **MoSDeF** tools permit simulation reproducibility across a variety of simulation engines,
removing the requirement of expert knowledge in all the engines to repeat, continue, or advance the existing research.
Additionally, the **MoSDeF** software permits the auto-generation of numerous and distinct systems, allowing large-scale screening of materials and chemicals via `Signac <https://signac.io>`_ to manage the simulations and data.

The `MoSDeF <https://mosdef.org>`_ software ecosystem contains the following packages:
    	* `mBuild <https://mbuild.mosdef.org/en/stable/>`_ -- A hierarchical, component based molecule builder

    	* `foyer <https://foyer.mosdef.org/en/stable/>`_ -- A package for atom-typing as well as applying and disseminating forcefields

    	* `GMSO <https://gmso.mosdef.org/en/stable/>`_ -- Flexible storage of chemical topology for molecular simulation


The using MoSDeF software to setup the GOMC and NAMD simulations, is made even easier via the `GOMC-MoSDeF documentation <http://gomc.eng.wayne.edu/documentation/>`_, which contains links to the GOMC Manual, and the `GOMC-MoSDeF tutorial files <https://github.com/GOMC-WSU/GOMC-MoSDeF>`_ with `GOMC YouTube tutorial videos <https://youtube.com/playlist?list=PLdxD0z6HRx8Y9VhwcODxAHNQBBJDRvxMf>`_. The GOMC-MoSDeF's PDB, PSF, and force field files are identical to the NAMD files for the traditional chemical engineering simulations, unless there are fixed bonds and angles in the GOMC force field files.  Changing the fixed bonds and angles between the GOMC and NAMD force field files is as simple as changing one (1) variable and rerunning that line of code.



Non-Traditional Chemical Engineering Systems
-------

Non-Traditional chemical engineering systems are proteins or other molecules requiring multiple residue names per molecule. Currently, the GOMC-MoSDeF software is not compatible with these systems.  Therefore, these systems should be constructed using different software, such as `Visual Molecular Dynamics (VMD) <https://www.ks.uiuc.edu/Research/vmd/>`_, or other similar software.

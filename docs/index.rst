
py-MCMD: A Python Library for Performing  Hybrid Monte Carlo - Molecular Dynamics Simulations with GOMC and NAMD
--------

This Python code enables hybrid molecular dynamics/Monte Carlo (MD/MC) simulations using `NAMD <https://www.ks.uiuc.edu/Research/namd/>`_ and the `GPU Optimized Monte Carlo (GOMC) <http://gomc.eng.wayne.edu>`_ software.
The Python code allows users to switch back and forth between the NAMD and GOMC simulation engines, with one (1) iteration of each NAMD and GOMC consisting of a cycle.  The user programs the number of cycles and the number of NAMD and GOMC steps per cycle.  Combining the MD/MC simulations allows the best of both types of simulations while minimizing the downsides, and in some cases, enabling simulations that were previously not feasible. This code allows the modification of the NAMD and GOMC control files, maximizing user flexibility and functionality.


This code distribution also contains the `Concatenate DCD (CatDCD) <https://www.ks.uiuc.edu/Development/MDTools/catdcd/>`_ software.
The py-MCMD Python package consists of two (2) different licenses (:download:`Combined_Licenses <../LICENSE>`), or they are available individually:

* One (1) license is for the NAMD_GOMC hybrid Python code, which initiates and organizes the individual simulations.

		Download as :download:`NAMD_GOMC_license <_images/NAMD_GOMC_license>`

		.. image:: https://img.shields.io/badge/License-GPLv3-blue.svg
			:target: www.gnu.org/licenses/gpl-3.0.en.html

* One (1) license is for the `Concatenate DCD (CatDCD) <https://www.ks.uiuc.edu/Development/MDTools/catdcd/>`_ software which is used to combine the DCD files produced by the py-MCMD Python package.

		Download as :download:`CatDCD_license <_images/CatDCD_license>`


.. toctree::
	installation
	simulation_parameters_files
	running_the_simulation
	simulation_output
	simulation_analysis
	running_analysis_code
	example_simulation
	CatDCD_instructions_license
	generating_systems
	citing_MDMC_PYTHON

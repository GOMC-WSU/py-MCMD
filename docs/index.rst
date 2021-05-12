
NAMD_GOMC - A Hybrid MD/MC Simulation Software
--------

This Python enables hybrid molecular dynamics/Monte Carlo (MD/MC) simulations using `NAMD <https://www.ks.uiuc.edu/Research/namd/>`_ and the `GPU Optimized Monte Carlo (GOMC) <http://gomc.eng.wayne.edu>`_ software..
The Python code allows users to switch back and forth between the NAMD and GOMC simulation engines, with one (1) iteration of each NAMD and GOMC consisting of a cycle.  The user programs the number of cycles and the number of NAMD and GOMC steps desired per cycle.  Combining the MD/MC simulations allows the best of both types of simulations while minimizing the downsides, and in some cases, enables simulations that were previously not feasible. This code allows the modification of the NAMD and GOMC control, maximizing user flexibility and functionality. 

This Python code is compatible only with `NAMD version 2.13-2.14 <https://www.ks.uiuc.edu/Development/Download/download.cgi?PackageName=NAMD>`_ and `GOMC-development branch <https://github.com/GOMC-WSU/GOMC/tree/development>`_.  The NAMD and GOMC software needs to be installed before using this hybrid python code. Please refer to the NAMD and GOMC software instructions for installing them.


**NOTE:**  GOMC does not currently use improper or Urey—Bradley potentials, so if the hybrid simulations contain impropers or Urey—Bradleys, the NAMD simulation energies will be different.  In a protein simulation, it should be OK not to use impropers or Urey-Bradleys in GOMC and utilize them in NAMD since the protein will not move in the GOMC simulation due to its size.  Each simulation will need to be individually evaluated to determine if not having the impropers or Urey-Bradleys in GOMC is irrelevant or significant to the simulation results.  

This code distribution also contains the `Concatenate DCD (CatDCD) <https://www.ks.uiuc.edu/Development/MDTools/catdcd/>`_ software.  
The NAMD_GOMC Python package consists of two (2) different licenses :download:`Combined_License <../LICENSE>`
or they are available individually:

* One (1) license is for the NAMD_GOMC hybrid Python code for the NAMD_GOMC hybrid code.  

		Download as :download:`NAMD_GOMC_license <files/NAMD_GOMC_license>`

		.. image:: https://img.shields.io/github/license/bc118/NAMD_GOMC
			:target: www.gnu.org/licenses/gpl-3.0.en.html

* One (1) license is for the `Concatenate DCD (CatDCD) <https://www.ks.uiuc.edu/Development/MDTools/catdcd/>`_ software which are used to combine the DCD files produced by the NAMD_GOMC Python package.   

		Download as :download:`CatDCD_license <files/CatDCD_license>`

.. toctree::
	installation
	simulation_parameters
	simulation_analysis
	example_simulation
	CatDCD_instructions_license
	citing_MDMC_PYTHON



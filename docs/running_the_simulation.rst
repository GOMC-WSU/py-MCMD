Running the Simulation
===============

The hybrid NAMD/GOMC simulation can be conducted once the *"user_input_NAMD_GOMC.json"* file is properly filled out to the user's specifications, including generating or obtaining the proper PSF, PDB, and force field (.inp or .par files) and specifying their proper paths.  

**WARNING:** Any hybrid simulation that encounters a NAMD simulation with zero atoms or non-fixed atoms will fail.  This failure will likely appear as a seg-fault in GOMC.  Currently, these types of simulations are not possible with this software.

Example # 1: GEMC Ensemble
---------------

Use a terminal window and move to the directory which contains the *run_NAMD_GOMC.py* file. Then run hybrid NAMD/GOMC simulations with the NAMD simulations for box 0 and box 1 executed in parallel (assuming both boxes are being simulated in NAMD per the *“user_input_NAMD_GOMC.json”* file).

	.. code:: ipython3

   		cd "directory_containing_run_NAMD_GOMC.py"

		python run_NAMD_GOMC.py -f user_input_NAMD_GOMC.json -namd_sims_order parallel



Example # 2: GCMC Ensemble
---------------

Use a terminal window and move to the directory which contains the *run_NAMD_GOMC.py* file. Then run hybrid NAMD/GOMC simulations.  

**NOTE:** The NAMD simulations default too in series, but it does not matter since the GCMC simulations box 1 is solely used as a reservoir without the need to evaluate the box's dynamics.  

	.. code:: ipython3

   		cd "directory_containing_run_NAMD_GOMC.py"

		python run_NAMD_GOMC.py -f user_input_NAMD_GOMC.json 


Flags for Running the Hybrid Simulation
---------------

The flags for running the *run_NAMD_GOMC.py* file user_input_variables_NAMD_GOMC.json file, or whatever the user names it. 
	
	-f *or* --file : json file
		Defines the variable inputs file used for the hybrid NAMD/GOMC simulation script.
		This file, the *"user_input_variables_NAMD_GOMC.json"* file, is required 
		to run the hybrid simulation.

	-namd_sims_order *or* --namd_simulation_order : default='series',  (options: 'series' or 'parallel')
		This sets the NAMD simulation to be run in series or parallel. The data is entered only as series or parallel (default = series). This is only relevant for the GEMC ensemble when utilizing two (2) NAMD simulation boxes (i.e., only_use_box_0_for_namd_for_gemc = False  --> both box 0 and box 1). The GCMC, NVT, NPT, or the GEMC ensembles when using only one (1) NAMD simulation box (i.e., only_use_box_0_for_namd_for_gemc = True --> only box 0) are always run in series, since there is nothing to run in parallel. Note: This feature was added so the user can minimize the load on the GPU by running both NAMD simulations in parallel.
		

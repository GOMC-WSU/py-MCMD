Simulation Analysis (post-simulation)
===============

The post-simulation analysis is required to combine all the individual simulation files into the combined molecular trajectories or coordinate (DCD file), system energies, and system State properties.  The systems topology (PSF) file is not combined, but selected and copied to the combined data for easy use.
Otherwise, without a data combining code, it would be nearly impossible to sort through all the individual GOMC and NAMD files and combine them all.  
The output from the combining file is dependent on the data input file (**user_input_combine_data_NAMD_GOMC.json** file) and the possibilities given the utilized ensemble.  The simulation data combining file also works for this hybrid software, and it also works for the GOMC-only or NAMD-only simulations, so the data is output in the same manner for easy comparison, if needed.  The following sections show how the combining data file outputs the data for the hybrid simulations.  While the NAMD-only and GOMC-only simulation combined data are not shown, they contain their own specific subset of the data.



Hybrid Simulation: NAMD Combined Energy Data
---------------

These combined NAMD outputs contain the **Energy and State properties** for the NAMD simulations.  Each file also include the header/title, which is only printed once at the top of the files.  A few NAMD output files are provided for easy utilization by the user. In these files the energy units are kcal/mol and the density is in g/cm^3

*  **NAMD_data_box_0.txt** = The energy rows from each individual NAMD simulation are extracted directly from the NAMD log file and combined into a single file with the corrected time steps.  

* **NAMD_data_density_box_0.txt** = The energy rows from each individual NAMD simulation are extracted directly from the NAMD log file with the **addition of the system density (g/cm^3)** and combined into a single file with the corrected time steps. 

	**NOTE:** For a hybrid simulation with the GEMC ensemble, box 1 would also be output as the files **NAMD_data_box_1.txt** and **NAMD_data_density_box_1.txt**.


Hybrid Simulation: GOMC Combined Energy Data
---------------

The combined GOMC outputs contain the **Energy and State properties** for the GOMC simulations, which are listed in two (2) separate lines (i.e., for example, ENER_0 and STAT_0 for box 0 or ENER_1 and STAT_1 for box 1).
Each file also include the header/title, which is only printed once at the top of the files. 
There are several GOMC output files provided so the user has some options

**NOTE:** Box 1 is listed as an output in the below examples, is only printed for the GEMC ensemble since box 1 serves no meaning or is not present in the GCMC, NPT, and NVT ensembles.  


	* **GOMC_data_box_0.txt** and **GOMC_data_box_1.txt** = The Energy and Stat data are output for each simulation box as they are extracted exactly as is from the GOMC log file (energy units are in **K** and the density units are in **kg/m^3**).


	* **GOMC_Energies_Stat_box_0.txt** and **GOMC_Energies_Stat_box_1.txt** = The Energy and Stat data are extracted from the GOMC log file, and output for each simulation box after they are appended together as a single line with the ENER_0 and STAT_0 labels removed as they are extracted from the GOMC log file (energy units are in **K** and the density units are in **kg/m^3**).


	* **GOMC_Energies_Stat_kcal_per_mol_box_0.txt** and **GOMC_Energies_Stat_kcal_per_mol_box_1.txt** = The Energy and Stat data are extracted from the GOMC log file, and output for each simulation box after they are appended together as a single line with the ENER_0 and STAT_0 labels removed as they are extracted from the GOMC log file (energy units are in **kcal/mol** and the density units are in **g/cm^3**).


Hybrid Simulation: GOMC and NAMD Coordinates/Topology (DCD/PSF)
---------------

The GOMC and NAMD coordinate (DCD) and topology (PSF) files can be output using the combining data python code, per the users input.  However, for the GCMC and GEMC ensembles, only the PSF and DCD files are output for the GOMC simulation since a NAMD simulation is not currently capable of handling a changing number of atoms. For example, both the combined NAMD and GOMC PSF and DCD files can be output for the NPT and NVT ensembles, but only the GOMC PSF and DCD files can be output for the GCMC and GEMC ensembles.  The output will be as follows:

	**NOTE:** The box 1 PSF and DCD files will only be output for the GOMC simulation using the GEMC ensemble. 

	* **Output_data_merged.psf** = This is the topology (PSF) file, which is used with the combined coordinate (DCD) files to identify the bond, angles, dihedrals, impropers, and other atoms naming and properties. If this is for a GCMC or GEMC ensemble, the topology (PSF) file will contain atoms from both box 0 and box 1. 


	* **combined_box_0_GOMC_dcd_files.dcd** and **combined_box_1_GOMC_dcd_files.dcd**= The combined coordinate (DCD) files from all the individual **GOMC** simulations, or at the selected frequency set by the user input file for combining the data. 


	* **combined_box_0_NAMD_dcd_files.dcd** = The combined coordinate (DCD) files from all the individual **NAMD** simulations, or at the selected frequency set by the user input file for combining the data. This combined NAMD coordinate (DCD) is only output for the NPT and NVT ensembles. 



Hybrid GCMC Simulation: GOMC Histogram and Distribution Data 
---------------

The histogram and distribution data are combined and output only for a GOMC using the GCMC ensemble. Please refer to the `GOMC Manual <https://gomc.eng.wayne.edu/documentation/>`_ for more information on the histogram and distribution data.  The files are listed as follows.

	* **GOMC_hist_data_box_0.txt** = The combined histogram data for the individual simulations.

	* **GOMC_dist_data_box_0_res_or_mol_no_XXX.txt** = The combined distribution data for each molecule type in the individual simulations.  **There will be one (1) combined distribution data file generated for each molecule type in the simulation, and they will replace the no_XXX in the file name with no_1, no_2, etc.**



Hybrid, GOMC-only, or NAMD-only Combining Data Input Variables
---------------

These variable are used when running combining the data code for the hybrid MD/MC simulations.  However, they can also be used for the traditional GOMC-only or NAMD-only simulations, allowing the user to easily compare between the simulations.  The variable selected will determine how the data combining code functions and thus how the data is output. Therefore, the user should ensure that the selected variables are in-line with the simulation which was conducted, or the output data will be lacking or fail to be generated. 

The variable below are contained in the *"user_input_combine_data_NAMD_GOMC.json"* file, which is the in the *"NAMD_GOMC/analysis_combine_data"* directory.


	simulation_type : string (only 'GEMC', 'GCMC', 'NPT', 'NVT') 
		The simulation type or ensemble to use
		Note: only GEMC-NVT available currently: 'GEMC' = GEMC-NVT

	only_use_box_0_for_namd_for_gemc : bool (true or false)
		This chooses if you want to run both simulation boxes in NAMD
		when running the GEMC ensemble, or just box 0.
		true = NAMD runs only box 0 for GEMC
		false = NAMD runs box 0 and 1 for GEMC

	simulation_engine_options : string (only 'Hybrid' or 'GOMC-only') 
		The type of simulation you are combining.  
		Hybrid is the hybrid NAMD-GOMC simulations.
		'GOMC-only' is stand-alone GOMC simulation.
		'NAMD-only' is stand-alone NAMD simulation.
		When using the 'GOMC-only', or 'NAMD-only' the dcd combining
		options and catdcd program and path are not required

	gomc_or_namd_only_log_filename : string
		The relative path and file name of the log file for the 
		GOMC-only or NAMD-only simulation,
		which is used to create the same file format as the
		hybrid simulation combining files.   

	combine_namd_dcd_file : bool (true or false)
		This chooses if you want combine all the NAMD dcd files into one
		file for all the Hybrid NAMD simulations.  
		This option is only possible for "NVT" and "NPT" simulations. 
		simulations/ensembles (simulation_type). 
		true = combine all the NAMD dcd files 
		false = do not combine all the NAMD dcd files 
		This is not required for the when only combining the  
		'GOMC-only', or 'NAMD-only' data.

	combine_gomc_dcd_file : bool (true or false)
		This chooses if you want combine all the GOMC dcd files into one
		file for all the Hybrid GOMC simulations.  
		This option available for all the
		simulations/ensembles (simulation_type). 
		true = combine all the GOMC dcd files 
		false = do not combine all the GOMC dcd files 
		This is not required for the when only combining the  
		'GOMC-only', or 'NAMD-only' data.

	rel_path_to_combine_binary_catdcd : string (only 'Hybrid' or 'GOMC-only') 
		The relative path and file name to the catdcd, which are provided
		from the Theoretical and Compuational Biopyysisc group (VMD/NAMD development team)
		(https://www.ks.uiuc.edu/Development/MDTools/catdcd/). 
		This tool is used to combine the dcd files for the hybrid simulations.
		This is not required for the when only combining the  
		'GOMC-only', or 'NAMD-only' data.
		
	rel_path_to_NAMD_and_GOMC_folders : string 
		The relative path to the main NAMD and GOMC folders which contain
		all the individual simulations.  This is also where the run_NAMD_GOMC.py
		file is located, as it build the NAMD and GOMC folders in the same 
		directory.




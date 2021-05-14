## Notes

- (1) GOMC does not currently use improper or Urey?Bradley potentials, so if the hybrid simulations contain impropers or Urey?Bradleys, the NAMD simulation energies will be different. In a protein simulation, it should be OK not to use impropers or Urey-Bradleys in GOMC and utilize them in NAMD since the protein will not move in the GOMC simulation due to its size. Each simulation will need to be individually evaluated to determine if not having the impropers or Urey-Bradleys in GOMC is irrelevant or significant to the simulation results.

## TO RUN hybrid simulations
- (1) Change the variables in the user_input_variables_NAMD_GOMC.json file, or whatever the user names it. 
	
	total_cycles_namd_gomc_sims : integer
		The total number of simulation cycles, where a cycle is a NAMD and 
		GOMC simulation. 		
		total_cycles_namd_gomc_sims = (NAMD_simulations + GOMC_simulations)/2

	starting_at_cycle_namd_gomc_sims : integer
		The cycle number to start the simulations at.  
		Enter zero for intial simualtion start, or non-zero for a restart.
		A new simulation would be started at zero (0).
		To restart a simulation, the last full cycle number of the 
		simulation would be entered.

	gomc_use_CPU_or_GPU : string (only 'CPU' or 'GPU')
		Run the GOMC simulation using the CPU or GPU.
		Note: For the NAMD simulation, the user will have to provide the 
		path to the GPU or CPU NAMD version.  (i.e., This function does not
		set NAMD's CPU or GPU version).  

	simulation_type : string (only 'GEMC', 'GCMC', 'NPT', 'NVT') 
		The simulation type or ensemble to use
		Note: only GEMC-NVT available currently: 'GEMC' = GEMC-NVT

	only_use_box_0_for_namd_for_gemc : bool (true or false)
		This chooses if you want to run both simulation boxes in NAMD
		when running the GEMC ensemble, or just box 0.
		true = NAMD runs only box 0 for GEMC
		false = NAMD runs box 0 and 1 for GEMC

	no_core_box_0 : integer (> 0)
		Number of CPU cores to use for box 0.  This is the ONLY place to enter CPU cores for 
		'GCMC', 'NPT', 'NVT', and  'GEMC' and only_use_box_0_for_namd_for_gemc = True
		Note: The total simulation core = no_core_box_0 + no_core_box_1, when using the
		(GEMC' and only_use_box_0_for_namd_for_gemc = False) values.  
		Note: If using the 'GCMC', 'NPT', 'NVT', or 
		(GEMC' and only_use_box_0_for_namd_for_gemc = True) ensembles, 
		the total simulation cores = no_core_box_0, regardless of the no_core_box_1 value.

	no_core_box_1 : integer (>= 0)  
		Number or CPU cores to use in box 1.  This always ZERO for 'GCMC', 'NPT', 'NVT' (>= 0).  
		Only use when 'GEMC' and only_use_box_0_for_namd_for_gemc = True (> 0)  
		Note: The total simulation core = no_core_box_0 + no_core_box_1, when using the
		(GEMC' and only_use_box_0_for_namd_for_gemc = False) values.  
		Note: If using the 'GCMC', 'NPT', 'NVT', or 
		(GEMC' and only_use_box_0_for_namd_for_gemc = True) ensembles, 
		the total simulation cores = no_core_box_0, regardless of the no_core_box_1 value.	
		
	simulation_temp_k : float or integer 
		GOMC and NAMD units of temperature are in Kelvin.

	simulation_pressure_bar : float or integer 
		GOMC and NAMD units of pressure are in bar (1.01325 bar = 1 atm).

	GCMC_ChemPot_or_Fugacity : None or string (only stings are 'ChemPot' or 'Fugacity')
		GCMC ensemble only: The variable used in the to control the GCMC ensemble.
		Choose either None, 'ChemPot' or 'Fugacity'

	GCMC_ChemPot_or_Fugacity_dict = {str (residue name up to 4 characters): int or float (see below)}
		GCMC ensemble only: The selected residue, which is a molecule, its 
		chemical potential (ChemPot) or fugacity (Fugacity).
		GCMC_ChemPot_or_Fugacity_dict = {str (Residue name): int or float 
		(ChemPots in unit GOMC K units or Fugacity in unit bar)}
		Example Chempot: GCMC_ChemPot_or_Fugacity_dict = {'TIP3': 1000, 'Cl' : -1000, 'Na' : -900}
		Example Fugacity (values >=0): GCMC_ChemPot_or_Fugacity_dict = {'TIP3': 1000, 'Cl' : 10, 'Na' : 0}

	namd_minimize_mult_scalar : int (>=0)   
		The scalar multiple used to get the number of NAMD minimization steps for this 
		intitial NAMD simulation.
		NAMD_minimize steps = namd_run_steps * namd_minimize_mult_scalar
		
	namd_run_steps : int (>=10)  
		The number of steps to run each cycle of the NAMD simulation.
		Needs to be 10 minimum for now, NEEDS TO BE THE SAME AS THE PREVIOUS SIMULATION, IF RESTARTED!

	gomc_run_steps : int (>=10)  
		The number of steps to run each cycle of the GOMC simulation.
		Needs to be 10 minimum for now, NEEDS TO BE THE SAME AS THE PREVIOUS SIMULATION, IF RESTARTED!

	set_dims_box_0_list : list or null, [null or float or int (>0), null or float or int (>0), null or float or int (>0)]
		The x, y, and z-dimensions of length for box 0 in Angstrom units.
		This is a list of 3, which can contain a null, float or int (>0).
		The length is auto read from the PDB files CRYST1 line, if it is containted there. 
		This command overrides the PDB value(s), and is needed for the simulation if 
		the data is not in the pdb file.
		Note: if null is used instead of a list the PDB values will be used.
		Note: if null is used instead of the x, y, or z-dimension, the
		PDB file will be used for the null dimensions. Example: [10, null, null],
		the x dimension would use 10 and the y and z dimensions would be the PDB
		file values. 

	set_dims_box_1_list : list or null, [null or float or int (>0), null or float or int (>0), null or float or int (>0)]
		The x, y, and z-dimensions of length for box 1 in Angstrom units.
		This is a list of 3, which can contain a null, float or int (>0).
		The length is auto read from the PDB files CRYST1 line, if it is containted there. 
		This command overrides the PDB value(s), and is needed for the simulation if 
		the data is not in the pdb file.
		Note: if null is used instead of a list the PDB values will be used.
		Note: if null is used instead of the x, y, or z-dimension, the
		PDB file will be used for the null dimensions. Example: [10, null, null],
		the x dimension would use 10 and the y and z dimensions would be the PDB
		file values. 

	set_angle_box_0_list : list or null, [null or float or int, null or float or int, null or float or int]
		The alpha, beta, and gamma angles for box 0 in degrees.
		This is a list of 3, which can contain a null, float or int.
		The angles are auto read from the PDB files CRYST1 line, if it is containted there. 
		This command overrides the PDB value(s), and is needed for the simulation if 
		the data is not in the pdb file.
		Note: if null is used instead of a list the PDB values will be used.
		Note: if null is used instead of the alpha, beta, and gamma angles, the
		PDB file will be used for the null dimensions. Example: [10, null, null],
		the alpha angle would use 10 and the beta and gamma angles would be the PDB
		file values. 
		NOTE: CURRENTLY ONLY ORTHOGONAL BOXES ARE AVAILABLE, SO ONLY NULL OR 90 
		WILL BE ACCEPTED. NULL WILL AUTO DEFAUT TO 90.  

	set_angle_box_1_list : list or null, [null or float or int, null or float or int, null or float or int]
		The alpha, beta, and gamma angles for box 1 in degrees.
		This is a list of 3, which can contain a null, float or int.
		The angles are auto read from the PDB files CRYST1 line, if it is containted there. 
		This command overrides the PDB value(s), and is needed for the simulation if 
		the data is not in the pdb file.
		Note: if null is used instead of a list the PDB values will be used.
		Note: if null is used instead of the alpha, beta, and gamma angles, the
		PDB file will be used for the null dimensions. Example: [10, null, null],
		the alpha angle would use 10 and the beta and gamma angles would be the PDB
		file values. 
		NOTE: CURRENTLY ONLY ORTHOGONAL BOXES ARE AVAILABLE, SO ONLY NULL OR 90 
		WILL BE ACCEPTED. NULL WILL AUTO DEFAUT TO 90.  

	starting_ff_file_list_gomc : list of strings
		All the force fields for the GOMC simulation.
		The strings in the list must be the relative path and file name to the force field(s) 
		Example : ["required_data/equilb_box_298K/GOMC_TIPS3P_FF.inp", "required_data/equilb_box_298K/GOMC_NaCl_FF.inp"]

	starting_ff_file_list_namd : list of strings
		All the force fields for the NAMD simulation.
		The strings in the list must be the relative path and file name to the force field(s) 
		Example : ["required_data/equilb_box_298K/NAMD_TIPS3P_FF.inp", "required_data/equilb_box_298K/NAMD_NaCl_FF.inp"]

	starting_pdb_box_0_file : string
		The relative path and filename to the starting PDB file for box 0, 
		which is initally fed to the NAMD simulation since it starts first.
		The string in the list must be the relative path to the force fields and the file name 
		Example : "required_data/equilb_box_298K/TIPS3P_box_0.pdb"

	starting_psf_box_0_file : string
		The relative path and filename to the starting PSF file box 0, 
		which is initally fed to the NAMD simulation since it starts first.
		The string in the list must be the relative path to the force fields and the file name 
		Example : "required_data/equilb_box_298K/TIPS3P_box_0.psf

	starting_pdb_box_1_file : string
		The relative path and filename to the starting PDB file for box 1, 
		which is initally fed to the NAMD simulation since it starts first.
		The string in the list must be the relative path to the force fields and the file name 
		Note: this is only needed for the "GCMC" and "GEMC" ensembles/simulation types
		Example : "required_data/equilb_box_298K/TIPS3P_box_1.pdb"

	starting_psf_box_1_file : string
		The relative path and filename to the starting PSF file box 1, 
		which is initally fed to the NAMD simulation since it starts first.
		The string in the list must be the relative path to the force fields and the file name 
		Note: this is only needed for the "GCMC" and "GEMC" ensembles/simulation types
		Example : "required_data/equilb_box_298K/TIPS3P_box_1.psf

	namd_bin_file : string
		The relative path to the directory where the namd2 file binary is located.
		This should be in the required_data/bin/NAMD212, or required_data/bin/NAMD212
		or required_data/bin directory. 
		IMPORTANT MANUAL MODIFICATION: To use the GPU and CPU or either version of namd, 
		the copied files in this directory must be renamed namd2_CPU and namd2_GPU.
		NOTE: THIS WAS ONLY TESTED ON NAMD VERSION 2.14, SO IT MAY NOT WORK ON OTHER 
		NAMD VERSIONS WITHOUT SOME CODE MODIFICATION.
		Alternatively, a sybolic link to namd2 file binary could be there.
		Example:  "required_data/bin/NAMD212"

	gomc_bin_file : string
		The relative path to the directory where the GOMC file binaries are located.
		This should be in the required_data/bin directory. 
		Alternatively, a sybolic link to GOMC file binaries file binary could be there.
		NOTE: THIS WAS ONLY TESTED ON THE GOMC DEVELOPMENT AFTER VERSION 2.70, 
		SO IT MAY NOT WORK ON OTHER GOMC VERSIONS WITHOUT SOME CODE MODIFICATION, 
		AND	SOME ADDITIONAL FUNCTIJONALLITY IS NOT IN PREVIOUS GOMC VERSIONS.
		Example: "required_data/bin"
	

- (2) If you have previous  "NAMD" and  "GOMC" folders in this directory deleted them, so you do not have mixed data in the simulation folders, unless this is desired. 
If they are not deleted the new data will overwrite the old data. 
 

- (3) Assuming that you have the packages installed or running anaconda env, if not install them.  Then run the hybrid simulations from its current directory with its json user variable file name (user_input_NAMD_GOMC.json) or whatever the user named it :

python run_NAMD_GOMC.py -f user_input_NAMD_GOMC.json  	or     python run_NAMD_GOMC.py --file user_input_NAMD_GOMC.json

or 

python run_NAMD_GOMC.py -f "user_set_name.json" 	 or     python run_NAMD_GOMC.py --file "user_set_name.json"


- (4) The simulation runs are sent to the "NAMD" and  "GOMC" folders, and the hybrid log file is in the same directory as the "run_NAMD_GOMC.py" file.





## Run the code to combine the data code (i.e., combine_data_NAMD_GOMC.py)

- (1) This file currently needs to be run from the directory with the "NAMD" and  "GOMC" folders !!!!


- (2) Download the The CatDCD - Concatenate DCD files (see reference information below) 
and put the catdcd-4.0b directory in the relative directory ->  required_data/bin .


- (3) Change the variables to the same as the ones used in the code:
	
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

- (4) Assuming that you have the packages installed or running anaconda env, if not install them.  Then run :

python combine_data_NAMD_GOMC.py -f user_input_combine_data_NAMD_GOMC.json 	 or     python combine_data_NAMD_GOMC.py --file user_input_combine_data_NAMD_GOMC.json      	# runs all the combining file data provided its in its current location

or 

python combine_data_NAMD_GOMC.py -f "user_set_name.json"	  or     python combine_data_NAMD_GOMC.py --file "user_set_name.json"


- (5) The combined data is now located in the "combined_data" folder, with the minimization run data removed (i.e., step 0 is the first step after the minimization.)





## References
- (1) The CatDCD - Concatenate DCD files code in this package was taken directly from the
	Theoretical and Compuational Biopyysisc group (VMD/NAMD development team)
	(https://www.ks.uiuc.edu/Development/MDTools/catdcd/). 
	This tool is used to combine the dcd files for the hybrid simulations, using the 
	rel_path_to_combine_binary_catdcd variable.



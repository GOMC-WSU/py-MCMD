Running the Combining Data Code
===============

The simulation analysis code is run via python and combines all the required data into a few files for an easy simulation analysis.  The data combining analysis code is located in the *"analysis_combine_data"* file directory in the main directory (i.e., *"NAMD_GOMC/analysis_combine_data"*). Before running the data combining analysis code, the user will need to fill out the proper input variables for the *"user_input_combine_data_NAMD_GOMC.json"*, which is located in the same directory since this file determines how the data combining code is processed. The *"user_input_combine_data_NAMD_GOMC.json"* file name can be changed to whatever the user desires.


This code is designed to combine the hybrid simulation data into a central location.  However, it can also be used to generate the same file types for a traditional NAMD-only or GOMC-only simulation, so the user can easily compare between the simulations.


Running the Combining Data Code
---------------

The combine data code is run from its file directory via a terminal window.  

**NOTE:** If the *"user_input_combine_data_NAMD_GOMC.json"* file variables are not set properly for the type of simulation that was conducted, the output will not work, or data will be missing. 

	.. code:: ipython3

   		cd "directory_containing_run_NAMD_GOMC.py"

		python run_NAMD_GOMC.py -f user_input_NAMD_GOMC.json -namd_sims_order parallel


Flags for Combining Data Code
---------------

	* **-f** or **--file** flag : json file 
		Defines the json file to use for variable inputs to the hybrid NAMD/GOMC, NAMD-only, or GOMC-only combining analysis script.

	* **-w** or **--write_folder_name** flag : str
		Defines the folder name which is created and contains the all the combined data.

	* **-o** or **--overwrite** flag : bool (True, true, T, t, False, false, F, or f)
		Determines whether to overwrite an exiting combined data folder and data, if they exist.

**NOTE:** If the *"user_input_combine_data_NAMD_GOMC.json"* file variable are not set properly for the type of simulation that was conducted, the output will not work or data will be missing. 



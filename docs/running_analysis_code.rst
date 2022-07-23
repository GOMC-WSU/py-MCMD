Running the Combining Data Code
===============

The simulation data combining code is run via Python and combines all the required data into a few files for an easy simulation analysis.  The data combining code is located in the main directory (i.e., *"py-MCMD/combine_data_NAMD_GOMC.py"*). Before running the data combining code, the user will need to fill out the proper input variables in the *"user_input_combine_data_NAMD_GOMC.json"* file, located in the same directory since this file determines how the data combining code is processed. The *"user_input_combine_data_NAMD_GOMC.json"* file name can be changed to whatever the user desires.


This code is designed to combine the hybrid simulation data into a central location.  However, it can also be used to generate the same file types for a traditional NAMD-only or GOMC-only simulation, so the user can easily compare between the simulations.


Executing the Combine Data Code
---------------

The combine data code is run from its file directory via a terminal window.

**NOTE:** If the *"user_input_combine_data_NAMD_GOMC.json"* file variables are not set properly for the type of simulation that was conducted, the output will not work, or data will be missing.

	.. code:: ipython3

   		cd "directory_containing_run_NAMD_GOMC.py"

		python combine_data_NAMD_GOMC.py -f user_input_combine_data_NAMD_GOMC.json -w combined_data -o False


Flags for Combining Data Code
---------------

	* **-f** *or* **--file** flag : json file
		Defines the json file to use for variable inputs to the hybrid NAMD/GOMC, NAMD-only, or GOMC-only combining code.

	* **-w** *or* **--write_folder_name** flag : str
		Defines the folder name which is created and contains the all the combined data files.

	* **-o** *or* **--overwrite** flag : (True, true, T, t, False, false, F, or f), default = False
		Determines whether to overwrite an exiting combined data folder and data, if they exist.


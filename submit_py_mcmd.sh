#!/bin/bash
#SBATCH --job-name="GEMC/py-MCMD"
#SBATCH --mem=20G
#SBATCH -t 111:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH -N 1
#SBATCH --ntasks-per-core=1

echo "Running on host $HOSTNAME"
echo "Time is $(date)"
source /home6/ia5498/.bashrc
cd /home6/ia5498/py-MCMD_tests/GEMC/350K

eval "$(conda shell.bash hook)"
conda activate mosdef

# Keep runtime files out of /dev/shm, which the system can wipe
export PY_MCMD_MANAGED_OUTPUT_ROOT=/tmp/py_mcmd_${SLURM_JOB_ID}
mkdir -p "$PY_MCMD_MANAGED_OUTPUT_ROOT"

echo "Starting py-MCMD $(date)"
python -m py_mcmd_refactored.cli.main -f user_input_NAMD_GOMC.json
echo "Ending py-MCMD $(date)"

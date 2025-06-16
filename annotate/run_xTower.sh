#!/bin/bash
#SBATCH --job-name=xtower_wmt2
#SBATCH --mail-user=a.karakanta@hum.leidenuniv.nl
#SBATCH --mail-type="ALL"
#SBATCH --time=04:00:00
#SBATCH --partition=gpu-short
#SBATCH --output=%x_%j.out
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=100G
#SBATCH --gres=gpu:a100:1

echo "## Starting GPU test on $HOSTNAME"


TEST_DIR=$(pwd)
echo "## Current dircectory $TEST_DIR"

echo "## Number of available CUDA devices: $CUDA_VISIBLE_DEVICES"

echo "## Checking status of CUDA device with nvidia-smi"
nvidia-smi


source /data1/karakantaa/venvs/xtower/bin/activate
export HF_HOME=/data1/karakantaa/.hfcache/

data_dir='/data1/karakantaa/EAMT25/02_data/'
spans=$data_dir/wmt24_spans/
out_dir=$data_dir/wmt24_explanations/

mkdir -p $out_dir

echo "Starting xTower"

for sfile in $spans/*.txt; do
	filename=$(basename "$sfile")
	outfile="$out_dir/$filename"
	echo "Processing... " $outfile
	python /data1/karakantaa/EAMT25/xTower.py "$sfile" "$outfile"
	echo "Generated explanations for " $filename
done

#! /usr/bin/env python3

import argparse
import logging
import os
import sys

import yaml

import misc.slurm as slurm
import misc.utils as utils


default_num_procs = 1
default_tmp = None # utils.abspath('tmp')
default_star_executable = "STAR"


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="This script runs the Rp-Bp and Rp-chi pipelines on a given sample. "
        "It requires a YAML config file that includes a number of keys. Please see the "
        "documentation for a complete description.")

    parser.add_argument('raw_data', help="The raw data file (fastq[.gz])")
    parser.add_argument('config', help="The (yaml) config file")
    parser.add_argument('name', help="The name for the dataset, used in the created files")

    parser.add_argument('--tmp', help="The temp directory for pybedtools", default=default_tmp)

    parser.add_argument('--star-executable', help="The name of the STAR executable",
        default=default_star_executable)
        
    parser.add_argument('--overwrite', help="If this flag is present, existing files "
        "will be overwritten.", action='store_true')
           
    slurm.add_sbatch_options(parser)
    utils.add_logging_options(parser)
    args = parser.parse_args()
    utils.update_logging(args)

    logging_str = utils.get_logging_options_string(args)

    config = yaml.load(open(args.config))
    call = not args.do_not_call


    # check that all of the necessary programs are callable
    programs =  [
                    'flexbar',
                    args.star_executable,
                    'samtools',
                    'bowtie2',
                    'bamToBed',
                    'fastaFromBed',
                    'create-base-genome-profile',
                    'remove-multimapping-reads',
                    'extract-metagene-profiles',
                    'estimate-metagene-profile-bayes-factors',
                    'select-periodic-offsets',
                    'extract-orf-profiles',
                    'smooth-orf-profiles',
                    'estimate-orf-bayes-factors',
                    'select-final-prediction-set',
                    'create-filtered-genome-profile',
                    'predict-translated-orfs'
                ]
    utils.check_programs_exist(programs)

    
    required_keys = [   
                        'riboseq_data',
                        'ribosomal_index',
                        'genome_base_path',
                        'genome_name',
                        'fasta',
                        'gtf',
                        'models_base'
                    ]
    utils.check_keys_exist(config, required_keys)

    
    # now, check if we want to use slurm
    msg = "use_slurm: {}".format(args.use_slurm)
    logging.debug(msg)

    if args.use_slurm:
        cmd = ' '.join(sys.argv)
        slurm.check_sbatch(cmd, args=args)
        return

    note_str = config.get('note', None)

    # the first step is the standard riboseq preprocessing
    
    # handle do_not_call so that we _do_ call the preprocessing script, but that it does not run anything
    do_not_call_str = ""
    if not call:
        do_not_call_str = "--do-not-call"

    overwrite_str = ""
    if args.overwrite:
        overwrite_str = "--overwrite"

    # for a sample, we first create its filtered genome profile
    star_str = "--star-executable {}".format(args.star_executable)

    tmp_str = ""
    if args.tmp is not None:
        tmp_str = "--tmp {}".format(args.tmp)

    cmd = ("create-filtered-genome-profile {} {} {} --num-cpus {} {} {} {} {} {}".format(args.raw_data, 
            args.config, args.name, args.num_cpus, do_not_call_str, overwrite_str, logging_str, star_str, tmp_str))

    utils.check_call(cmd)

    # then we predict the ORFs
    cmd = ("predict-translated-orfs {} {} --num-cpus {} {} {} {} {}".format(args.config, 
            args.name, args.num_cpus, tmp_str, do_not_call_str, overwrite_str, logging_str))
    utils.check_call(cmd)

if __name__ == '__main__':
    main()

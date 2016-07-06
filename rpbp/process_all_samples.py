#! /usr/bin/env python3

import argparse
import os
import yaml

import misc.slurm as slurm
import misc.utils as utils

import riboutils.ribo_utils as ribo_utils

default_num_procs = 1
default_tmp = None # utils.abspath('tmp')
default_star_executable = "STAR"

def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="This is a helper script which submits a set of samples to SLURM. It "
        "can also be used to run a set of samples sequentially. Due to limitations on "
        "the config file specification, all of the samples must use the same reference "
        "indices (i.e., genome sequence, set of ORFs, etc.).")

    parser.add_argument('config', help="The (yaml) config file")

    parser.add_argument('--tmp', help="The temp directory for pybedtools", default=default_tmp)
    parser.add_argument('--star-executable', help="The name of the STAR executable",
        default=default_star_executable)

    parser.add_argument('--overwrite', help="If this flag is present, existing files "
        "will be overwritten.", action='store_true')

    parser.add_argument('--merge-replicates', help="If this flag is present, then "
        "the ORF profiles from the replicates will be merged before making the final "
        "predictions", action='store_true')
    
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
                    'create-orf-profiles',
                    'predict-translated-orfs',
                    'run-rpbp-pipeline'
                ]
    utils.check_programs_exist(programs)

    
    required_keys = [   
                        'riboseq_data',
                        'riboseq_samples',
                        'ribosomal_index',
                        'star_index',
                        'genome_base_path',
                        'genome_name',
                        'fasta',
                        'gtf',
                        'models_base'
                    ]
    utils.check_keys_exist(config, required_keys)

    note = config.get('note', None)

    # handle do_not_call so that we _do_ call the pipeline script, but that it does not run anything
    do_not_call_str = ""
    if not call:
        do_not_call_str = "--do-not-call"
    args.do_not_call = False

    overwrite_str = ""
    if args.overwrite:
        overwrite_str = "--overwrite"

    # if we merge the replicates, then we only use the rpbp script to create
    # the ORF profiles
    profiles_only_str = ""
    if args.merge_replicates:
        profiles_only_str = "--profiles-only"
    
    star_str = "--star-executable {}".format(args.star_executable)
    tmp_str = ""
    if args.tmp is not None:
        tmp_str = "--tmp {}".format(args.tmp)
    
    # collect the job_ids in case we are using slurm and need to merge replicates
    job_ids = []

    for name, data in config['riboseq_samples'].items():

        tmp_str = ""
        if args.tmp is not None:
            tmp = os.path.join(args.tmp, "{}_{}_rpbp".format(name, note))
            tmp_str = "--tmp {}".format(tmp)

        cmd = "run-rpbp-pipeline {} {} {} --num-cpus {} {} {} {} {} {} {}".format(data, 
                args.config, name, args.num_cpus, tmp_str, do_not_call_str, 
                overwrite_str, logging_str, star_str, profiles_only_str)

        job_id = slurm.check_sbatch(cmd, args=args)

        job_ids.append(job_id)

    # now, if we are running the "standard" pipeline, we are finished
    if not args.merge_replicates:
        return

    # otherwise, we need to merge the replicates for each condition
    riboseq_replicates = ribo_utils.get_riboseq_replicates(config)
    merge_replicates_str = "--merge-replicates"

    for condition_name in riboseq_replicates.keys():
            
        # then we predict the ORFs
        cmd = ("predict-translated-orfs {} {} --num-cpus {} {} {} {} {} {}".format(args.config, 
                condition_name, args.num_cpus, tmp_str, do_not_call_str, overwrite_str, 
                logging_str, merge_replicates_str))

        slurm.check_sbatch(cmd, args=args, dependencies=job_ids)

if __name__ == '__main__':
    main()

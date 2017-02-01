from setuptools import find_packages, setup
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop

import importlib
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

###
#   If you receive an error like: NameError: name 'install' is not defined
#   Please make sure the most recent version of pip is installed
###

###
#   Most of this is taken from a template at:
#       http://diffbrent.ghost.io/correctly-adding-nltk-to-your-python-package-using-setup-py-post-install-commands/
###

external_requirements =  [
    'cython',
    'numpy',
    'scipy',
    'pandas',
    'joblib',
    'docopt',
    'tqdm',
    'statsmodels',
    'pysam',
    'pyfasta',
    'pystan',
    'pybedtools',
    'pyyaml',
    'psutil',
    'patsy' # no idea what this is for...
]

internal_requirements = {
    "misc[bio]":"-e git+https://bitbucket.org/bmmalone/misc.git#egg=misc[bio]",
     # the "-e" seems to be necessary to grab subfolders. I do not
     # understand this, but it seems to work
    "riboutils": "git+https://github.com/dieterich-lab/riboseq-utils.git#egg=riboutils"
}

stan_model_files = [
    os.path.join("nonperiodic", "no-periodicity.stan"),
    os.path.join("nonperiodic", "start-high-high-low.stan"),
    os.path.join("nonperiodic", "start-high-low-high.stan"),
    os.path.join("periodic", "start-high-low-low.stan"),
    os.path.join("untranslated", "gaussian-naive-bayes.stan"),
    os.path.join("translated", "periodic-gaussian-mixture.stan")
    #os.path.join("translated", "periodic-cauchy-mixture.stan"),
    #os.path.join("translated", "zero-inflated-periodic-cauchy-mixture.stan")
]

stan_pickle_files = [
    os.path.join("nonperiodic", "no-periodicity.pkl"),
    os.path.join("nonperiodic", "start-high-high-low.pkl"),
    os.path.join("nonperiodic", "start-high-low-high.pkl"),
    os.path.join("periodic", "start-high-low-low.pkl"),
    os.path.join("untranslated", "gaussian-naive-bayes.pkl"),
    os.path.join("translated", "periodic-gaussian-mixture.pkl")
    #os.path.join("translated", "periodic-cauchy-mixture.pkl"),
    #os.path.join("translated", "zero-inflated-periodic-cauchy-mixture.pkl")
]


def _post_install(self):
    import site
    importlib.reload(site)
    
    import riboutils.ribo_filenames as filenames
    import misc.shell_utils as shell_utils
    
    smf = [os.path.join("rpbp_models", s) for s in stan_model_files]

    models_base = filenames.get_default_models_base()
    spf = [os.path.join(models_base, s) for s in stan_pickle_files]

    # compile and pickle the stans models
    for stan, pickle in zip(smf, spf):
        if os.path.exists(pickle):
            msg = "A model alread exists at: {}. Skipping.".format(pickle)
            logging.warning(msg)
            continue

        # make sure the path exists
        dirname = os.path.dirname(pickle)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        cmd = "pickle-stan \"{}\" \"{}\"".format(stan, pickle)
        logging.info(cmd)
        subprocess.call(cmd, shell=True)

    # check for the prerequisite programs
    programs = ['flexbar']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='flexbar', logger=logger)
        
    programs = ['STAR']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='STAR', logger=logger)

    programs = ['bowtie2', 'bowtie2-build-s']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='bowtie2', logger=logger)

    programs = ['intersectBed', 'bedToBam']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='bedtools', logger=logger)

    programs = ['samtools']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='SAMtools', logger=logger)

    programs = ['gffread']
    shell_utils.check_programs_exist(programs, raise_on_error=False, 
        package_name='cufflinks', logger=logger)

def install_requirements(is_user):
    
    is_user_str = ""
    if is_user:
        is_user_str = "--user"

    option = "install {}".format(is_user_str)
    for package_name, location in internal_requirements.items():
        # check if this package is already installed
        package_spec = importlib.util.find_spec(package_name)
        found = package_spec is not None

        if not found:
            cmd = "pip3 {} {}".format(option, location)
            subprocess.call(cmd, shell=True)
    

class my_install(_install):
    def run(self):
        level = logging.getLevelName("INFO")
        logging.basicConfig(level=level,
            format='%(levelname)-8s : %(message)s')

        _install.run(self)
        install_requirements(self.user)
        _post_install(self)

class my_develop(_develop):  
    def run(self):
        level = logging.getLevelName("INFO")
        logging.basicConfig(level=level,
            format='%(levelname)-8s : %(message)s')

        _develop.run(self)
        install_requirements(self.user)
        _post_install(self)

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='rpbp',
        version='1.0',
        description="This package contains scripts for analyzing ribosome profiling data.",
        long_description=readme(),
        keywords="ribosome profiling bayesian inference markov chain monte carlo translation",
        url="",
        author="Brandon Malone",
        author_email="bmmalone@gmail.com",
        license='MIT',
        packages=find_packages(),
        install_requires = [external_requirements], # + internal_requirements,
        extras_require = {
            'analysis': ['matplotlib', 'matplotlib_venn', 'crimson>=0.1.1']
        },
        cmdclass={'install': my_install,  # override install
                  'develop': my_develop   # develop is used for pip install -e .
        },  

        include_package_data=True,
        test_suite='nose.collector',
        tests_require=['nose'],
        entry_points = {
            'console_scripts': [
                                'extract-orfs=rpbp.reference_preprocessing.extract_orfs:main',
                                'prepare-genome=rpbp.reference_preprocessing.prepare_genome:main',
                                'create-orf-profiles=rpbp.orf_profile_construction.create_orf_profiles:main',
                                'create-base-genome-profile=rpbp.orf_profile_construction.create_base_genome_profile:main',
                                'predict-translated-orfs=rpbp.translation_prediction.predict_translated_orfs:main',
                                'extract-orf-profiles=rpbp.orf_profile_construction.extract_orf_profiles:main',
                                'smooth-orf-profiles=rpbp.orf_profile_construction.smooth_orf_profiles:main',
                                'merge-replicate-orf-profiles=rpbp.translation_prediction.merge_replicate_orf_profiles:main',
                                'estimate-orf-bayes-factors=rpbp.translation_prediction.estimate_orf_bayes_factors:main',
                                'select-final-prediction-set=rpbp.translation_prediction.select_final_prediction_set:main',
                                'run-rpbp-pipeline=rpbp.run_rpbp_pipeline:main',
                                'process-all-samples=rpbp.process_all_samples:main',
                                'visualize-metagene-profile=rpbp.analysis.profile_construction.visualize_metagene_profile:main [analysis]',
                                'visualize-metagene-profile-bayes-factor=rpbp.analysis.profile_construction.visualize_metagene_profile_bayes_factor:main [analysis]',
                                'create-preprocessing-report=rpbp.analysis.profile_construction.create_preprocessing_report:main [analysis]',
                                'get-all-read-filtering-counts=rpbp.analysis.profile_construction.get_all_read_filtering_counts:main [analysis]',
                                'visualize-read-filtering-counts=rpbp.analysis.profile_construction.visualize_read_filtering_counts:main [analysis]',
                                'get-orf-peptide-matches=rpbp.analysis.proteomics.get_orf_peptide_matches:main [analysis]',
                                'extract-orf-types=rpbp.analysis.extract_orf_types:main [analysis]',
                                'get-all-orf-peptide-matches=rpbp.analysis.proteomics.get_all_orf_peptide_matches:main [analysis]',
                                'create-orf-peptide-coverage-line-graph=rpbp.analysis.proteomics.create_orf_peptide_coverage_line_graph:main [analysis]',
                                'create-proteomics-report=rpbp.analysis.proteomics.create_proteomics_report:main [analysis]',
                                'create-riboseq-test-dataset=rpbp.analysis.create_riboseq_test_dataset:main [analysis]',
                                'visualize-orf-type-metagene-profiles=rpbp.analysis.rpbp_predictions.visualize_orf_type_metagene_profiles:main [analysis]',
                                'create-orf-types-pie-chart=rpbp.analysis.rpbp_predictions.create_orf_types_pie_chart:main [analysis]',
                                'create-orf-length-distribution-line-graph=rpbp.analysis.rpbp_predictions.create_orf_length_distribution_line_graph:main [analysis]',
                                'create-predictions-report=rpbp.analysis.rpbp_predictions.create_predictions_report:main [analysis]',
                                'create-bf-rpkm-scatter-plot=rpbp.analysis.rpbp_predictions.create_bf_rpkm_scatter_plot:main [analysis]',
                                'match-orfs-with-qti-seq-peaks=rpbp.analysis.qti_seq.match_orfs_with_qti_seq_peaks:main [analysis]',
                                'match-orfs-with-mackowiak-sorfs=rpbp.analysis.conservation.match_orfs_with_mackowiak_sorfs:main [analysis]',
                                'perform-mackowiak-permutation-test=rpbp.analysis.conservation.perform_mackowiak_permutation_test:main [analysis]',
                                'filter-nonunique-peptide-matches=rpbp.analysis.proteomics.filter_nonunique_peptide_matches:main [analysis]',
                                'add-mygene-info-to-orfs=rpbp.analysis.rpbp_predictions.add_mygene_info_to_orfs:main [analysis]'
                               ]
        },
        zip_safe=False
        )

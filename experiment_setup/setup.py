"""PySurfexExpSetup functionality."""
import sys
from argparse import ArgumentParser
import os
import logging
import experiment
try:
    import surfex
except:
    surfex = None


def surfex_exp_setup():
    kwargs = parse_surfex_script_setup(sys.argv[1:])
    surfex_script_setup(**kwargs)


def parse_surfex_script_setup(argv):
    """Parse the command line input arguments."""
    parser = ArgumentParser("Surfex offline setup script")
    parser.add_argument('-exp_name', dest="exp", help="Experiment name", type=str, default=None)
    parser.add_argument('--wd', help="Experiment working directory", type=str, default=None)

    # Setup variables
    parser.add_argument('-rev', dest="rev", help="Surfex experiement source revison", type=str,
                        required=False, default=None)
    parser.add_argument('-experiment', dest="pysurfex_experiment",
                        help="Pysurfex-experiment library", type=str, required=True, default=None)
    parser.add_argument('-offline', dest="offline_source", help="Offline source code", type=str,
                        required=False, default=None)
    parser.add_argument('-namelist', dest="namelist_dir", help="Namelist directory", type=str,
                        required=False, default=None)
    parser.add_argument('-host', dest="host", help="Host label for setup files", type=str,
                        required=False, default=None)
    parser.add_argument('--config', help="Config", type=str, required=False, default=None)
    parser.add_argument('--config_file', help="Config file", type=str, required=False, default=None)
    parser.add_argument('--debug', dest="debug", action="store_true", help="Debug information")
    # parser.add_argument('--version', action='version', version=__version__)

    if len(argv) == 0:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args(argv)
    kwargs = {}
    for arg in vars(args):
        kwargs.update({arg: getattr(args, arg)})
    return kwargs


def surfex_script_setup(**kwargs):
    """Do experiment setup.

    Raises:
        Exception: _description_
        Exception: _description_
        Exception: _description_
        Exception: _description_

    """
    debug = kwargs.get("debug")
    if debug is None:
        debug = False
    if debug:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)
    logging.info("************ PySurfexExpSetup ******************")

    # Setup
    exp_name = kwargs.get("exp")
    wdir = kwargs.get("wd")
    pysurfex = f"{os.path.dirname(surfex.__file__)}/../"
    pysurfex_experiment = kwargs.get("pysurfex_experiment")
    offline_source = kwargs.get("offline_source")
    namelist_dir = kwargs.get("namelist_dir")
    host = kwargs.get("host")
    if host is None:
        raise Exception("You must set a host")

    config = kwargs.get("config")
    config_file = kwargs.get("config_file")

    # Find experiment
    if wdir is None:
        wdir = os.getcwd()
        logging.info("Setting current working directory as WD: %s", wdir)
    if exp_name is None:
        logging.info("Setting EXP from WD: %s", wdir)
        exp_name = wdir.split("/")[-1]
        logging.info("EXP = %s", exp_name)

    if offline_source is None:
        logging.warning("No offline soure code set. Assume existing binaries")

    exp_dependencies = experiment.ExpFromFiles.setup_files(wdir, exp_name, host, pysurfex,
                                                           pysurfex_experiment,
                                                           offline_source=offline_source,
                                                           namelist_dir=namelist_dir)

    experiment.ExpFromFiles.write_exp_config(exp_dependencies, configuration=config,
                                             configuration_file=config_file)

    exp_dependencies = experiment.ExpFromFiles.setup_files(wdir, exp_name, host, pysurfex,
                                                           pysurfex_experiment,
                                                           offline_source=offline_source,
                                                           namelist_dir=namelist_dir,
                                                           talk=False)

    exp_dependencies_file = wdir + "/exp_dependencies.json"
    experiment.ExpFromFiles.dump_exp_dependencies(exp_dependencies, exp_dependencies_file)

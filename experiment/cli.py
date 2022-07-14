"""Client interfaces for offline experiment scripts."""
import sys
from argparse import ArgumentParser
from datetime import datetime
import os
import shutil
import logging
import experiment


def parse_surfex_script(argv):
    """Parse the command line input arguments."""
    parser = ArgumentParser("Surfex offline run script")
    parser.add_argument('action', type=str, help="Action",
                        choices=["start", "prod", "continue", "testbed",
                                 "install", "climate", "co"])
    parser.add_argument('-exp_name', dest="exp", help="Experiment name", type=str, default=None)
    parser.add_argument('--wd', help="Experiment working directory", type=str, default=None)

    parser.add_argument('-dtg', help="DateTimeGroup (YYYYMMDDHH)", type=str, required=False,
                        default=None)
    parser.add_argument('-dtgend', help="DateTimeGroup (YYYYMMDDHH)", type=str, required=False,
                        default=None)
    parser.add_argument('--suite', type=str, default="surfex", required=False,
                        help="Type of suite definition")
    parser.add_argument('--stream', type=str, default=None, required=False, help="Stream")

    # co
    parser.add_argument("--file", type=str, default=None, required=False, help="File to checkout")

    parser.add_argument('--debug', dest="debug", action="store_true", help="Debug information")
    parser.add_argument('--version', action='version', version=experiment.__version__)

    if len(argv) == 0:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args(argv)
    kwargs = {}
    for arg in vars(args):
        kwargs.update({arg: getattr(args, arg)})
    return kwargs


def surfex_script(**kwargs):
    """Modify or start an experiment suite.

    Raises:
        NotImplementedError: _description_
        Exception: _description_
        Exception: _description_
        Exception: _description_
        Exception: _description_
        Exception: _description_
    """
    debug = kwargs.get("debug")
    if debug is None:
        debug = False
    if debug:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(pathname)s:%(lineno)s %(message)s',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

    logging.info("************ PySurfexExp ******************")

    action = kwargs["action"]
    exp = kwargs.get("exp")

    # Co
    file = kwargs["file"]

    # Others
    dtg = kwargs["dtg"]
    dtgend = kwargs["dtgend"]
    suite = kwargs["suite"]

    begin = kwargs.get("begin")
    if begin is None:
        begin = True

    work_dir = kwargs.get("wd")

    # Find experiment
    if work_dir is None:
        work_dir = os.getcwd()
        logging.info("Setting current working directory as WD: %s", work_dir)
    if exp is None:
        logging.info("Setting EXP from WD: %s", work_dir)
        exp = work_dir.split("/")[-1]
        logging.info("EXP = %s", exp)

    libs = ["surfex", "scheduler", "experiment"]
    for lib in libs:
        if os.path.exists(work_dir + "/" + lib):
            sys.path.insert(0, work_dir + "/" + lib)
            logging.debug("Set first in system path: %s/%s", work_dir, lib)

    if "action" == "mon":
        # TODO

        raise NotImplementedError
    elif action == "co":
        if file is None:
            raise Exception("Checkout requires a file (--file)")
        experiment.ExpFromFiles(exp, work_dir).checkout(file)
    else:
        # Some kind of start
        if action == "start" and dtg is None:
            raise Exception("You must provide -dtg to start a simulation")
        elif action == "climate":
            if dtg is None:
                dtg = "2008061600"
            if suite is not None and suite != "climate":
                raise Exception("Action was climate but you also specified a suite not being " +
                                + f"climate: {suite}")
            suite = "climate"
        elif action == "testbed":
            if dtg is None:
                dtg = "200806160000"
            if suite is not None and suite != "testbed":
                raise Exception("Action was climate but you also specified a suite not being " +
                                + f"testbed: {suite}")
            suite = "testbed"
        elif action == "install":
            if dtg is None:
                dtg = "200806160000"
            suite = "Makeup"

        progress_file = work_dir + "/progress.json"
        progress_pp_file = work_dir + "/progressPP.json"

        progress = None
        if action.lower() == "prod" or action.lower() == "continue":
            progress = experiment.ProgressFromFile(progress_file, progress_pp_file)
            if dtgend is not None:
                progress.dtgend = datetime.strptime(dtgend, "%Y%m%d%H%M")
        else:
            if action == "start":
                if dtg is None:
                    raise Exception("No DTG was provided!")

                # Convert dtg/dtgend to datetime
                if isinstance(dtg, str):
                    if len(dtg) == 10:
                        dtg = datetime.strptime(dtg, "%Y%m%d%H")
                    elif len(dtg) == 12:
                        dtg = datetime.strptime(dtg, "%Y%m%d%H%M")
                    else:
                        raise Exception("DTG must be YYYYMMDDHH or YYYYMMDDHHmm")
                if isinstance(dtgend, str):
                    if len(dtgend) == 10:
                        dtgend = datetime.strptime(dtgend, "%Y%m%d%H")
                    elif len(dtgend) == 12:
                        dtgend = datetime.strptime(dtgend, "%Y%m%d%H%M")
                    else:
                        raise Exception("DTGEND must be YYYYMMDDHH or YYYYMMDDHHmm")
                # Read progress from file. Returns None if no file exists or not set.
                progress = experiment.ProgressFromFile(progress_file, progress_pp_file)

                dtgbeg = dtg
                if dtgend is None:
                    dtgend = progress.dtgend
                progress = experiment.Progress(dtg, dtgbeg, dtgend=dtgend)

        # Update progress
        if progress is not None:
            progress.save(progress_file, progress_pp_file, indent=2)

        # Set experiment from files. Should be existing now after setup
        exp_dependencies_file = work_dir + "/paths_to_sync.json"
        sfx_exp = experiment.ExpFromFiles(exp_dependencies_file)
        system = sfx_exp.system

        data0 = system.get_var("SFX_EXP_DATA", "0")
        lib0 = system.get_var("SFX_EXP_LIB", "0")
        logfile = data0 + "/ECF.log"

        # Create exp scheduler json file
        sfx_exp.write_scheduler_info(logfile)

        # Create LIB0 and copy init run if WD != lib0
        if work_dir.rstrip("/") != lib0.rstrip("/"):
            ecf_init_run = lib0 + "/ecf/InitRun.py"
            dirname = os.path.dirname(ecf_init_run)
            dirs = dirname.split("/")
            if len(dirs) > 1:
                fpath = "/"
                for dname in dirs[1:]:
                    fpath = fpath + str(dname)
                    # print(p)
                    os.makedirs(fpath, exist_ok=True)
                    fpath = fpath + "/"
            shutil.copy2(work_dir + "/ecf/InitRun.py", ecf_init_run)

        # Create and start the suite
        def_file = f"{data0}/{suite}.def"

        defs = experiment.get_defs(sfx_exp, system, progress, suite)
        defs.save_as_defs(def_file)
        sfx_exp.server.start_suite(defs.suite_name, def_file, begin=begin)


def parse_update_config(argv):
    """Parse the command line input arguments."""
    parser = ArgumentParser("Update Surfex offline configuration")
    parser.add_argument('-exp_name', dest="exp", help="Experiment name", type=str, default=None)
    parser.add_argument('--wd', help="Experiment working directory", type=str, default=None)
    parser.add_argument('--debug', dest="debug", action="store_true", help="Debug information")
    parser.add_argument('--version', action='version', version=experiment.__version__)

    args = parser.parse_args(argv)
    kwargs = {}
    for arg in vars(args):
        kwargs.update({arg: getattr(args, arg)})
    return kwargs


def update_config(**kwargs):
    """Update the experiment json file configurations."""
    debug = kwargs.get("debug")
    if debug is None:
        debug = False
    if debug:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(pathname)s:%(lineno)s %(message)s',
                            level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

    exp = kwargs.get("exp")

    work_dir = kwargs.get("wd")

    # Find experiment
    if work_dir is None:
        work_dir = os.getcwd()
        logging.info("Setting current working directory as WD: %s", work_dir)
    if exp is None:
        logging.info("Setting EXP from WD: %s", work_dir)
        exp = work_dir.split("/")[-1]
        logging.info("EXP = %s", exp)

    # Set experiment from files. Should be existing now after setup
    exp_dependencies_file = f"{work_dir}/paths_to_sync.json"
    sfx_exp = experiment.ExpFromFiles(exp_dependencies_file)
    system = sfx_exp.system

    data0 = system.get_var("SFX_EXP_DATA", "0")
    logfile = data0 + "/ECF.log"

    # Create exp scheduler json file
    sfx_exp.write_scheduler_info(logfile)
    logging.info("Configuration was updated!")

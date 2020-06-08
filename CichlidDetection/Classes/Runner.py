import argparse, os, sys, subprocess
from CichlidDetection.Classes.DataPreppers import DataPrepper
from CichlidDetection.Classes.FileManagers import FileManager
from CichlidDetection.Utilities.system_utilities import run

# main script


class Runner:
    def __init__(self):
        self.fm = FileManager()
        self.dp = DataPrepper(self.fm)
        self.__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        pass

    def prep_yolo(self, pids='All'):
        if pids is 'All':
            pids = self.fm.get_all_pids()
        for pid in pids:
            self.fm = FileManager(pid)
            self.dp = DataPrepper(self.fm)
            self.dp.YOLO_prep()

    def train_yolo(self):
        model_dir = os.path.join(self.__location__, 'Classes', 'Models', 'YOLO')
        pbs_file = os.path.join(model_dir, 'train.pbs')
        data_file = self.fm.local_files['data_file']
        cmd = ['qsub', '-v', 'DATA_FILE={},MODEL_DIR={}'.format(data_file, model_dir), pbs_file]
        run(cmd)
        print('training initiated. Use qstat to check job status')

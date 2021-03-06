import os, shutil
from os.path import join, basename, exists
from CichlidDetection.Classes.FileManager import FileManager, ProjectFileManager
from CichlidDetection.Utilities.utils import xywh_to_xyminmax
from shapely.geometry import Polygon
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
import random


def area(row, poly_vps):
    """calculate the annotation box area

    Args:
        row: pandas dataframe row containing, at minimum, the box coordinates (in x, y, w, h form) and project id
        poly_vps (dict): dictionary of video crops as Shapely Polygons, keyed by project id

    Returns:
        float: annotation area if the box is within the video crop boundaries, else np.nan
    """
    x_a, y_a, w_a, h_a = row['Box']
    poly_ann = Polygon([[x_a, y_a], [x_a + w_a, y_a], [x_a + w_a, y_a + h_a], [x_a, y_a + h_a]])
    intersection_area = poly_ann.intersection(poly_vps[row['ProjectID']]).area
    ann_area = poly_ann.area
    return ann_area if ann_area == intersection_area else np.nan


class DataPrepper:
    """class to handle the required data prep prior to training the model"""
    def __init__(self):
        """initiate a FileManager object, and and empty dictionary to store a ProjectFileManager object for each project"""
        self.file_manager = FileManager()
        self.proj_file_managers = {}

    def download_all(self):
        """initiate a ProjectFileManager for each unique project. This automatically downloads any missing files"""
        for pid in self.file_manager.unique_pids:
            self.proj_file_managers.update({pid: ProjectFileManager(pid, self.file_manager)})

    def prep(self):
        """prep the label files, image files, and train-test lists required for training"""
        if not self.proj_file_managers:
            self.download_all()
        good_images = self.prep_labels()
        self.prep_images(good_images)
        self.generate_ground_truth_csv()

    def prep_labels(self):
        """generate a label file for each valid image

        valid images are those in the boxed fish csv for which CorrectAnnotation is Yes, Sex is m or f, Nfish > 0, and
        the annotation box falls entirely within the boundaries defined by the video points numpy file

        Returns:
            list: file names of the images valid for training/testing
        """
        # load the boxed fish csv
        df = pd.read_csv(self.file_manager.local_files['boxed_fish_csv'], index_col=0)
        # drop empty frames, incorrectly annotated frames, and frames where any fish is labeled 'u'
        u_frames = df[df.Sex == 'u'].Framefile.unique()
        df = df[(df.Nfish != 0) & (df.CorrectAnnotation == 'Yes') & (~df.Framefile.isin(u_frames))]

        # drop annotation boxes outside the area defined by the video points numpy
        df['Box'] = df['Box'].apply(eval)
        poly_vps = {}
        for pfm in self.proj_file_managers.values():
            poly_vps.update({pfm.pid: Polygon([list(row) for row in list(np.load(pfm.local_files['video_points_numpy']))])})
        df['Area'] = df.apply(lambda row: area(row, poly_vps), axis=1)
        df = df.dropna(subset=['Area'])
        # convert the 'Box' tuples to min and max x and y coordinates
        df[['xmin', 'ymin', 'w', 'h']] = pd.DataFrame(df['Box'].tolist(), index=df.index)
        df['xmax'] = df.xmin + df.w
        df['ymax'] = df.ymin + df.h
        df['label'] = [1 if sex == 'f' else 2 for sex in df.Sex]
        # trim down to only the required columns
        df = df.set_index('Framefile')
        df = df[['xmin', 'ymin', 'xmax', 'ymax', 'label']]
        # write a labelfile for each image remaining in df
        good_images = list(df.index.unique())
        for f in good_images:
            dest = join(self.file_manager.local_files['label_dir'], f.replace('.jpg', '.txt'))
            df.loc[[f]].to_csv(dest, sep=' ', header=False, index=False)
        return good_images

    def prep_images(self, good_images, train_size=0.8, inject_empties=True):
        """populate the train and test image directories and create corresponding train and test lists

        Args:
            good_images (list of str): file names of valid images to move
            train_size (float): the proportion of 'good images' to use in the training set
            inject_empties (bool): if True (default), inject empty frames into the test set
        """
        source_paths = []
        for pid in self.file_manager.unique_pids:
            proj_image_dir = self.proj_file_managers[pid].local_files['project_image_dir']
            candidates = os.listdir(proj_image_dir)
            proj_images = [img for img in good_images if img in candidates]
            source_paths.extend([join(proj_image_dir, fname) for fname in proj_images])

        train_files, test_files = train_test_split(source_paths, train_size=train_size, random_state=42)
        source_paths = {'train': train_files, 'test': test_files}
        for subset in ('train', 'test'):
            for source in source_paths[subset]:
                dest = join(self.file_manager.local_files['{}_image_dir'.format(subset)], basename(source))
                if not exists(dest):
                    shutil.copy(source, dest)

        train_files, test_files = (sorted([basename(f) for f in f_list]) for f_list in (train_files, test_files))
        if inject_empties:
            test_files = self._inject_empties(test_files)

        with open(self.file_manager.local_files['train_list'], 'w') as f:
            f.writelines('{}\n'.format(f_) for f_ in sorted(train_files))
        with open(self.file_manager.local_files['test_list'], 'w') as f:
            f.writelines('{}\n'.format(f_) for f_ in sorted(test_files))

    def generate_ground_truth_csv(self):
        """generate a csv of testing targets for comparison with the output of Trainers.Trainer._evaluate_epoch()"""
        # load the boxed fish csv and narrow to valid images
        df = pd.read_csv(self.file_manager.local_files['boxed_fish_csv'])
        # parse the test list from test_list.txt
        with open(self.file_manager.local_files['test_list']) as f:
            frames = [basename(frame) for frame in f.read().splitlines()]
        # narrow dataframe to images in the test list
        df = df.loc[df.Framefile.isin(frames) & (df.CorrectAnnotation == 'Yes') & (df.Sex != 'u'), :]
        df = df[['Framefile', 'Box', 'Sex']]
        # coerce the values into the correct form
        df.Sex = df.Sex.apply(lambda x: [1] if x is 'f' else [2] if x is 'm' else [])
        df['Box'] = df['Box'].apply(lambda x: list(eval(x)) if type(x) is str else [])
        df['Box'] = df['Box'].apply(lambda x: xywh_to_xyminmax(*x) if x else x)
        df.rename(columns={'Box': 'boxes', 'Sex': 'labels'}, inplace=True)
        df = df.groupby('Framefile').agg({'boxes': list, 'labels': 'sum'})
        df.boxes = df.boxes.apply(lambda x: [] if x == [[]] else x)
        df.to_csv(self.file_manager.local_files['ground_truth_csv'])

    def _inject_empties(self, test_files, target_ratio=0.2):
        """add empty frames to the test set

        Args:
            test_files (list of str): file names of images already in the test set
            target_ratio (float): target ratio of empty to non-empty frames in the test set. Actual ratio may be smaller
                if there aren't enough unique empty frames to reach the target ratio
        Returns:
            updated test file list
        """
        target_num_empties = int(len(test_files) * (target_ratio/(1-target_ratio)))
        df = pd.read_csv(self.file_manager.local_files['boxed_fish_csv'])
        empty_frames = df[(df.Nfish == 0) & (df.CorrectAnnotation == 'Yes')].Framefile.tolist()
        if len(empty_frames) > target_num_empties:
            random.seed(42)
            empty_frames = random.choices(empty_frames, k=target_num_empties)
        test_files.extend(empty_frames)
        test_files = sorted(test_files)

        source_paths = []
        for pid in self.file_manager.unique_pids:
            proj_image_dir = self.proj_file_managers[pid].local_files['project_image_dir']
            candidates = os.listdir(proj_image_dir)
            proj_images = [img for img in empty_frames if img in candidates]
            source_paths.extend([join(proj_image_dir, fname) for fname in proj_images])

        for source in source_paths:
            dest = join(self.file_manager.local_files['test_image_dir'], basename(source))
            if not exists(dest):
                shutil.copy(source, dest)

        return test_files




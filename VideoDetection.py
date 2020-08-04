# to create videoloaders for the detection script
import os
from os.path import join
from torch.utils.data import Dataset
import cv2
import numpy as np
import torch
from PIL import Image
from torch import tensor
from CichlidDetection.Utilities.utils import run, make_dir
from CichlidDetection.Classes.FileManager import FileManager
from CichlidDetection.Classes.FileManager import ProjectFileManager
from CichlidDetection.Utilities.ml_utils import collate_fn, Compose, ToTensor, RandomHorizontalFlip
from CichlidDetection.Classes.Detector import Detector

class VideoDataset(Dataset):

    def __init__(self, video_file, transform=None):
        self.transforms = transform
        cap = cv2.VideoCapture(video_file)
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.framerate = int(cap.get(cv2.CAP_PROP_FPS))
        self.len = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.start_time = 0
        self.stop_time = int(self.len / self.framerate) - 1

        self.frames = np.empty(shape=(self.height, self.width, self.stop_time - self.start_time), dtype='uint8')

        count = 0
        for i in range(self.start_time, self.stop_time):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i * self.framerate))
            ret, frame = cap.read()
            if not ret:
                print('Couldnt read frame ' + str(i) in args.Videofile + '. Using last good frame', file=sys.stderr)
                self.frames[:, :, count] = self.frames[:, :, count - 1]

            else:
                self.frames[:, :, count] = 0.2125 * frame[:, :, 2] + 0.7154 * frame[:, :, 1] + 0.0721 * frame[:, :, 0]

            count += 1


    def __getitem__(self, idx):
        # if torch.is_tensor(idx):
        #     idx = idx.tolist()

        # print(self.frames[idx], self.frames[idx].shape)
        # img = Image.fromarray(self.frames[idx])
        # print(self.transforms)
        img = self.frames[idx]
        target = {'image_id': tensor(idx)}
        if self.transforms is not None:
            img, target = self.transforms(img, target)
        return img, target

    def __len__(self):
        return self.len

fm = FileManager()
# pfm = ProjectFileManager('MC6_5', fm, False, True, '0005_vid.mp4')
videoLoader = VideoDataset('/data/scratch/CichlidDetection/detection/short_ten.mp4', Compose([RandomHorizontalFlip(0.5), ToTensor()]))
de = Detector()
# for i in videoLoader:
#     print(i)
de.frame_detect(videoLoader)

from PIL import Image
from CichlidDetection.Classes.FileManager import FileManager
import torch
from torch import tensor


def read_label_file(path):
    """read box coordinates and labels from the label file and return them as a target dictionary.

    Args:
        path (str): path to label file

    Returns:
        dict: target dictionary containing the boxes tensor and labels tensor
    """
    boxes = []
    labels = []
    with open(path) as f:
        for line in f.readlines():
            values = line.split()
            boxes.append([float(val) for val in values[:4]])
            labels.append(int(values[4]))
    boxes = torch.as_tensor(boxes, dtype=torch.float32)
    labels = torch.as_tensor(labels, dtype=torch.int64)
    return {'boxes': boxes, 'labels': labels}


class DataLoader(object):
    """Class to handle loading of training or testing data"""
    def __init__(self, transforms, subset):
        """initialize DataLoader

        Args:
            transforms: Composition of Pytorch transformations to apply to the data when loading
            subset (str): data subset to use, options are 'train' and 'test'
        """
        self.fm = FileManager()
        self.files_list = self.fm.local_files['{}_list'.format(subset)]
        self.transforms = transforms

        # open either train_list.txt or test_list.txt and read the image file names
        with open(self.files_list, 'r') as f:
            self.img_files = sorted(f.read().splitlines())
        # generate a list of matching label file names
        self.label_files = [fname.replace('.jpg', '.txt') for fname in self.img_files]
        self.label_files = [fname.replace('images', 'labels') for fname in self.label_files]

    def __getitem__(self, idx):
        """get the image and target corresponding to idx

        Args:
            idx (int): image ID number, 0 indexed

        Returns:
            tensor: img, a tensor image
            dict of tensors: target, a dictionary containing the following
                'boxes', a size [N, 4] tensor of target annotation boxes
                'labels', a size [N] tensor of target labels (one for each box)
                'image_id', a size [1] tensor containing idx
        """
        # read in the image and label corresponding to idx
        img = Image.open(self.img_files[idx]).convert("RGB")
        target = read_label_file(self.label_files[idx])
        # add idx to the target dict as 'image_id'
        target.update({'image_id': tensor([idx])})
        # apply any necessary transforms to the image and target
        if self.transforms is not None:
            img, target = self.transforms(img, target)
        return img, target

    def __len__(self):
        return len(self.img_files)
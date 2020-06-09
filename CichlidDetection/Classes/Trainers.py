import os
import numpy as np
import time
from PIL import Image

import pdb

from CichlidDetection.Utilities.utils import Logger, AverageMeter, collate_fn
import CichlidDetection.Utilities.transforms as T

from CichlidDetection.Classes.DataLoaders import DataLoader
from CichlidDetection.Classes.DataPreppers import DataPrepper
from CichlidDetection.Classes.FileManagers import FileManager

import torch
import torchvision
from torch import optim

class Trainer:

    def __init__(self):
        self.fm = FileManager()
        self._initiate_loaders()
        self._initiate_model()

    def train(self):

    def _initiate_loaders(self):
        train_dataset = DataLoader(self._get_transform(train=True), 'train')
        test_dataset = DataLoader(self._get_transform(train=False), 'test')
        self.train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=5, shuffle=True, num_workers=2, pin_memory=True, collate_fn=collate_fn)
        self.test_loader = torch.utils.data.DataLoader(
            test_dataset, batch_size=5, shuffle=False, num_workers=2, pin_memory=True, collate_fn=collate_fn)

    def _initiate_model(self):
        self.model = torchvision.models.detection.fasterrcnn_resnet50_fpn(num_classes=2)
        self.parameters = self.model.parameters()
        self.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        self.model.to(self.device)

    def _get_transform(self, train):
        transforms = [T.ToTensor]
        if train:
            transforms.append(T.RandomHorizontalFlip(0.5))
        return T.Compose(transforms)

    def _train_epoch(self, epoch, data_loader, model,  optimizer, epoch_logger, batch_logger, device):
        print('train at epoch {}'.format(epoch))
        model.train()

        batch_time = AverageMeter()
        data_time = AverageMeter()
        losses = AverageMeter()
        end_time = time.time()

        for i, (images, targets) in enumerate(data_loader):
            data_time.update(time.time() - end_time)
            images = list(image.to(device) for image in images)
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            loss_dict = model(images, targets)
            today_loss = sum(loss for loss in loss_dict.values())
            losses.update(today_loss.item(), len(images))

            optimizer.zero_grad()
            today_loss.backward()
            optimizer.step()

            batch_time.update(time.time() - end_time)
            end_time = time.time()

            batch_logger.log({
                'epoch': epoch,
                'batch': i + 1,
                'iter': (epoch - 1) * len(data_loader) + (i + 1),
                'loss': losses.val,
                'lr': optimizer.param_groups[0]['lr']
            })

            print('Epoch: [{0}][{1}/{2}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  .format(
                      epoch,
                      i + 1,
                      len(data_loader),
                      batch_time=batch_time,
                      data_time=data_time,
                      loss=losses))
        epoch_logger.log({
            'epoch': epoch,
            'loss': losses.avg,
            'lr': optimizer.param_groups[0]['lr']
        })
        return losses.avg

def main():

    


    


    

# define training and validation data loaders

    optimizer = optim.SGD(parameters, lr=0.005,
                                momentum=0.9, weight_decay=0.0005)
    # and a learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, 'min', patience=5)
            
            
    # create logger files
    train_logger = Logger(
            os.path.join(dp.master_dir, 'train.log'),
            ['epoch', 'loss', 'lr'])
    train_batch_logger = Logger(
            os.path.join(dp.master_dir, 'train_batch.log'),
            ['epoch', 'batch', 'iter', 'loss', 'lr'])
    
    val_logger = Logger(
            os.path.join(dp.master_dir, 'val.log'), ['epoch', 'loss'])
    # let's train it for 10 epochs
    num_epochs = 20
    
    for epoch in range(num_epochs):
        # train for one epoch, printing every 10 iterations
#         train_one_epoch(model, optimizer, train_loader, device, epoch, print_freq=10)
        loss = train_epoch(epoch, train_loader, model, optimizer,train_logger, train_batch_logger,device)
        # update the learning rate
        scheduler.step(loss)
        # evaluate on the test dataset
#         evaluate(model, data_loader_test, device=device)
    print("Done!")

if __name__ == "__main__":
    main()

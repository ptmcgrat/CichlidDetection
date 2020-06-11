import os
import numpy as np
import time


from CichlidDetection.Utilities.utils import Logger, AverageMeter, collate_fn
import CichlidDetection.Utilities.transforms as T

from CichlidDetection.Classes.DataLoaders import DataLoader
from CichlidDetection.Classes.FileManagers import FileManager

import torch
import torchvision
from torch import optim

class Trainer:

    def __init__(self, num_epochs):
        self.fm = FileManager()
        self.num_epochs = num_epochs
        self._initiate_loaders()
        self._initiate_model()
        self._initiate_loggers()

    def train(self):
        for epoch in range(self.num_epochs):
            loss = self._train_epoch(epoch)
            self.scheduler.step(loss)
            # self._evaluate_epoch(epoch)
        self._save_model()

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
        self.optimizer = optim.SGD(self.parameters, lr=0.005, momentum=0.9, weight_decay=0.0005)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, 'min', patience=5)

    def _initiate_loggers(self):
        self.train_logger = Logger(self.fm.local_files['train_log'], ['epoch', 'loss', 'lr'])
        self.train_batch_logger = Logger(self.fm.local_files['batch_log'], ['epoch', 'batch', 'iter', 'loss', 'lr'])
        self.val_logger = Logger(self.fm.local_files['val_log'], ['epoch'])

    def _get_transform(self, train):
        transforms = [T.ToTensor()]
        if train:
            transforms.append(T.RandomHorizontalFlip(0.5))
        return T.Compose(transforms)

    def _train_epoch(self, epoch):
        print('train at epoch {}'.format(epoch))
        self.model.train()

        batch_time = AverageMeter()
        data_time = AverageMeter()
        losses = AverageMeter()
        end_time = time.time()

        for i, (images, targets) in enumerate(self.train_loader):
            data_time.update(time.time() - end_time)
            images = list(image.to(self.device) for image in images)
            targets = [{k: v.to(self.device) for k, v in t.items()} for t in targets]
            loss_dict = self.model(images, targets)
            today_loss = sum(loss for loss in loss_dict.values())
            losses.update(today_loss.item(), len(images))

            self.optimizer.zero_grad()
            today_loss.backward()
            self.optimizer.step()

            batch_time.update(time.time() - end_time)
            end_time = time.time()

            self.train_batch_logger.log({
                'epoch': epoch,
                'batch': i + 1,
                'iter': (epoch - 1) * len(self.train_loader) + (i + 1),
                'loss': losses.val,
                'lr': self.optimizer.param_groups[0]['lr']
            })

            print('Epoch: [{0}][{1}/{2}]\t'
                  'Time {batch_time.val:.3f} ({batch_time.avg:.3f})\t'
                  'Data {data_time.val:.3f} ({data_time.avg:.3f})\t'
                  'Loss {loss.val:.4f} ({loss.avg:.4f})\t'
                  .format(
                      epoch,
                      i + 1,
                      len(self.train_loader),
                      batch_time=batch_time,
                      data_time=data_time,
                      loss=losses))
        self.train_logger.log({
            'epoch': epoch,
            'loss': losses.avg,
            'lr': self.optimizer.param_groups[0]['lr']
        })
        return losses.avg

    @torch.no_grad()
    def _evaluate_epoch(self, epoch):
        print('evaluating epoch {}'.format(epoch))
        box_preds_csv = open(self.fm.local_files['box_predictions_csv'], 'a')
        label_preds_csv = open(self.fm.local_files['label_predictions_csv'], 'a')
        self.model.eval()
        for i, (images, targets) in enumerate(self.test_loader):
            images = list(image.to(self.device) for image in images)
            if i == 0:
                box_preds_csv.write(targets)
            output = self.model(images)

        self.val_logger.log({
            'epoch': epoch
        })
        box_preds_csv.close()
        label_preds_csv.close()

    def _save_model(self):
        dest = self.fm.local_files['weights_file']
        if os.path.exists(dest):
            path = os.path.join(self.fm.local_files['weights_dir'], str(int(os.path.getmtime(dest))) + '.weights')
            os.rename(dest, path)
        torch.save(self.model.state_dict(), dest)







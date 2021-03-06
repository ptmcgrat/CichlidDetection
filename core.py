import argparse
import subprocess
import os
import socket

"""primary command line executable script."""

# example usage
# python3 core.py full_auto -e 10 --Dry

# parse command line arguments
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(help='Available Commands', dest='command')

download_parser = subparsers.add_parser('download')

train_parser = subparsers.add_parser('train')
train_parser.add_argument('-e', '--Epochs', type=int, default=10, help='number of epochs to train')

full_auto_parser = subparsers.add_parser('full_auto')
full_auto_parser.add_argument('-e', '--Epochs', type=int, default=10, help='number of epochs to train')

sync_parser = subparsers.add_parser('sync')

detect_parser = subparsers.add_parser('detect')
detect_parser.add_argument('-t', '--Test', action='store_true', help='run detection on 10 images from the test set')
detect_parser.add_argument('-v', '--Video', action='store_true', help='run detection on complete video')
detect_parser.add_argument('-i', '--ImgDir', type=str, default='detection/images',
                           help='path, relative to ~/scratch/CichlidDetection, containing the images to analyze')

args = parser.parse_args()

# determine the absolute path to the directory containing this script, and the host name
package_root = os.path.dirname(os.path.abspath(__file__))
host = socket.gethostname()

# if running from a PACE login node, assert that args.command == full_auto, then submit the train.pbs script
if ('login' in host) and ('pace' in host):
    assert (args.command == 'full_auto'), 'full_auto is the only mode currently on a PACE login node'
    pbs_dir = os.path.join(package_root, 'CichlidDetection/PBS')
    subprocess.run(['qsub', 'train.pbs', '-v', 'EPOCHS={}'.format(args.Epochs)], cwd=pbs_dir)

# if not on a PACE login node, begin the analysis specified by args.command
else:
    if args.command == 'sync':
        from CichlidDetection.Classes.FileManager import FileManager
        FileManager().sync_training_dir()

    else:
        from CichlidDetection.Classes.Runner import Runner
        runner = Runner()

        if args.command == 'full_auto':
            runner.download()
            runner.prep()
            runner.train(num_epochs=args.Epochs)

        elif args.command == 'download':
            runner.download()

        elif args.command == 'train':
            runner.prep()
            runner.train(num_epochs=args.Epochs)

        elif args.command == 'detect':
            if args.Test:
                runner.detect('test')
            elif args.Video:
                runner.detect('fullvideo')
            else:
                runner.detect(args.ImgDir)

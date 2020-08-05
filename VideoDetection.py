import argparse
import os
from CichlidDetection.Classes.Detector import Detector
from CichlidDetection.Classes.FileManager import FileManager
from CichlidDetection.Classes.FileManager import ProjectFileManager
from CichlidDetection.Classes.VideoCreator import Animation

# parse command line arguments
parser = argparse.ArgumentParser(description='To Detect Cichlids in Videos')
parser.add_argument('pid', type=str, metavar=' ', help='Project ID. Ex: MC6_5')
parser.add_argument('video', type=str, metavar=' ', help='Run detection on specified video. Ex: 0005_vid.mp4')
parser.add_argument('-i', '--download_images', action='store_true', help='Download full image directory')
parser.add_argument('-v', '--download_video', action='store_true', help='Download video')
args = parser.parse_args()

"""
Download videos from different projects and run them through the model to detect cichlids

Args:
    pid (str): project id
    download_images (bool): if True, download the full image directory for the specified project
    download_videos (bool): if True, download the all the mp4 files in Videos directory for the specified project
    video (str): specifies which video to download
"""

fm = FileManager()
# Create project directory and download the specified files
pfm = ProjectFileManager(args.pid, fm, args.download_images, args.download_video, args.video)
detect = Detector()
video_path = os.path.join(fm.local_files['{}_dir'.format(args.pid)], args.video)
csv_file = detect.frame_detect(args.pid, video_path)
animation = Animation(args.pid, args.video, csv_file)
print('Detections video name:  ', animation)


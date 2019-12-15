# Author:   Marios Tsekitsidis
# Date:     December 16, 2019
# Version:  Python 2.7.13
# Purpose:  This script was written as part of the Final Project in C R P 556 (F19)


import arcpy
import datetime
import os
import subprocess
import time
import zipfile  # import standard modules
from box_walk import *  # import custom module


# 0. Setup


arcpy.CheckOutExtension('Spatial')  # check out Spatial Analyst extension


# 1. Download data


start = time.time()
os.chdir('data')  # step into data dir

# (a) download Iowa DEM data:

print 'Downloading counties DEM...'

bw = BoxWalker('https://iastate.box.com/s/dboob8jvve6qvk639smhbpsw0b7g4qbf', '5ZAvdQOpUaVeZBLlz2MYIY8BeKLNfiWW')
for x in bw.walk('52245723277', filters={'contains': 'DEM', 'endswith': '.zip'}):
    file_id, file_name = x
    try:
        r = requests.get('https://api.box.com/2.0/files/' + file_id + '/content', headers=bw.headers)
        with open(os.path.join('DEM_raw', file_name), 'wb') as y:
            y.write(r.content)
        with zipfile.ZipFile(os.path.join('DEM_raw', file_name), 'r') as z:
            z.extractall('DEM')
    except requests.exceptions.RequestException as e:
        print e  # print encountered error

# (b) download hydrology data for the VPUs which Iowa is a part of:

print 'Downloading hydrology data...'

base_url = 'http://www.horizon-systems.com/NHDPlusData/NHDPlusV21/Data/NHDPlusMS/'
rel_urls = ['NHDPlus07/NHDPlusV21_MS_07_VogelExtension_01.7z',  # Upper Mississippi 07
            'NHDPlus10U/NHDPlusV21_MS_10U_VogelExtension_02.7z',  # Upper Missouri 10U
            'NHDPlus10L/NHDPlusV21_MS_10L_VogelExtension_01.7z']  # Lower Missouri 10L

for vpu in rel_urls:
    try:
        r = requests.get(base_url + vpu)
        archive_name = vpu.split('/')[1]
        with open(archive_name, 'wb') as f:
            f.write(r.content)
        subprocess.call(
            r'"..\helpers\7-ZipPortable\App\7-Zip64\7z.exe" x ' + archive_name + ' -aoa' + ' -o' + 'NHDPlusMS_raw',
            stdout=open(os.devnull, 'wb')  # silent mode
        )
    except requests.exceptions.RequestException as e:
        print e  # print encountered error # TO-DO: change to logger

os.chdir('..')  # return to root dir

elapsed = time.time() - start
print 'Time elapsed downloading data: '+str(datetime.timedelta(seconds=elapsed))

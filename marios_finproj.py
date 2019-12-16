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

# prepare directory structure:

if not os.path.isdir('data'):
    os.mkdir('data')
os.chdir('data')  # step into data dir
subdirs = ['DEM', 'DEM_raw', 'NHDPlusMS', 'NHDPlusMS_raw']
for d in subdirs:
    if not os.path.isdir(d):
        os.mkdir(d)

# (a) download Iowa DEM data:

print 'Downloading DEM data...'

bw = BoxWalker('https://iastate.box.com/s/dboob8jvve6qvk639smhbpsw0b7g4qbf', 'UT9oEhoP5VrnHdFU0RbMpMVGHpa4czAM')

files = bw.walk('52245723277', filters={'contains': 'DEM', 'endswith': '.zip'})
for i in range(len(files)):
    if i % 10 == 0:
        print '  Downloading DEM for county ' + str(i + 1) + '/' + str(len(files)) + ' (' + str(
            len(files) - i) + ' left)...'
    file_id, file_name = files[i]
    try:
        r = requests.get('https://api.box.com/2.0/files/' + file_id + '/content', headers=bw.headers, stream=True)
        with open(os.path.join('DEM_raw', file_name), 'wb') as f:
            for block in r.iter_content(1024):
                f.write(block)
        with zipfile.ZipFile(os.path.join('DEM_raw', file_name), 'r') as z:
            z.extractall('DEM')
    except requests.exceptions.RequestException as e:
        print e  # print encountered error

print 'Done!'

# (b) download shapefile of Iowa flowline:

print 'Downloading hydrology data...'

try:
    r = requests.get('https://api.box.com/2.0/files/310185097791/content', headers=bw.headers, stream=True)
    with open('NHD_flowline_raw.zip', 'wb') as f:
        f.write(r.content)
    with zipfile.ZipFile('NHD_flowline_raw.zip', 'r') as z:
        z.extractall()
except requests.exceptions.RequestException as e:
    print e  # print encountered error

# (c) download flow velocity data for the VPUs which Iowa is a part of:

base_url = 'http://www.horizon-systems.com/NHDPlusData/NHDPlusV21/Data/NHDPlusMS/'
rel_urls = ['NHDPlus07/NHDPlusV21_MS_07_VogelExtension_01.7z',  # Upper Mississippi 07 - table
            'NHDPlus10U/NHDPlusV21_MS_10U_VogelExtension_02.7z',  # Upper Missouri 10U - table
            'NHDPlus10L/NHDPlusV21_MS_10L_VogelExtension_01.7z']  # Lower Missouri 10L - table

for vpu in rel_urls:
    try:
        r = requests.get(base_url + vpu, stream=True)
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

print('Done!')

elapsed = time.time() - start
print 'Time elapsed downloading data: ' + str(datetime.timedelta(seconds=elapsed))

# Author:   Marios Tsekitsidis
# Date:     December 16, 2019
# Version:  Python 2.7.13
# Purpose:  This script was written as part of the Final Project in C R P 556 (F19)

# import standard modules:
import arcpy
import datetime
import numpy as np
import os
import subprocess
import time
import zipfile
# import custom module:
from box_walk import *

############
# 0. Setup #
############

# check if output geodatabase exists; if not, create it:
cwd = os.getcwd()
hydroGDB = os.path.join(cwd, 'iowa_hydro.gdb')
if not arcpy.Exists(hydroGDB):
    arcpy.CreateFileGDB_management(os.path.dirname(hydroGDB), os.path.basename(hydroGDB))

# set up environments:
arcpy.env.scratchWorkspace = 'in_memory'
arcpy.env.workspace = hydroGDB
arcpy.env.overwriteOutput = True

arcpy.CheckOutExtension('Spatial')  # check out Spatial Analyst extension

start = time.time()
'''
#######################
# 1. Downloading data #
#######################

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

bw = BoxWalker('https://iastate.box.com/s/dboob8jvve6qvk639smhbpsw0b7g4qbf', '')

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

# (b) download flow velocity tables and flowline shapefiles for the VPUs which Iowa is a part of:

print 'Downloading hydrography data...'

base_url = 'http://www.horizon-systems.com/NHDPlusData/NHDPlusV21/Data/NHDPlusMS/'
rel_urls = ['NHDPlus07/NHDPlusV21_MS_07_VogelExtension_01.7z',  # Upper Mississippi 07 - table
            'NHDPlus10U/NHDPlusV21_MS_10U_VogelExtension_02.7z',  # Upper Missouri 10U - table
            'NHDPlus10L/NHDPlusV21_MS_10L_VogelExtension_01.7z',  # Lower Missouri 10L - table
            'NHDPlus07/NHDPlusV21_MS_07_NHDSnapshot_08.7z',  # Upper Mississippi 07 - shp
            'NHDPlus10U/NHDPlusV21_MS_10U_NHDSnapshot_07.7z',  # Upper Missouri 10U - shp
            'NHDPlus10L/NHDPlusV21_MS_10L_NHDSnapshot_06.7z']  # Lower Missouri 10L - shp

for vpu in rel_urls:
    try:
        r = requests.get(base_url + vpu, stream=True)
        archive_name = vpu.split('/')[1]
        os.chdir('NHDPlusMS_raw')
        with open(archive_name, 'wb') as f:
            for block in r.iter_content(1024):
                f.write(block)
        subprocess.call(
            r'"..\..\helpers\7-ZipPortable\App\7-Zip64\7z.exe" x ' + archive_name + ' -aoa' + ' -o' + '..',
            stdout=open(os.devnull, 'wb')  # silent mode
        )
        os.chdir('..')
    except requests.exceptions.RequestException as e:
        print e  # print encountered error # TO-DO: change to logger

print('Done!')

elapsed = time.time() - start
print 'Time elapsed downloading and extracting data: ' + str(datetime.timedelta(seconds=elapsed))

os.chdir('..')  # return to root dir

#####################
# 2. Pre-processing #
#####################

# copy tables and shp of interest into GDB:
for root, dirs, files in os.walk(os.path.join('data', 'NHDPlusMS')):
    for f in files:
        if 'vogel' in f.lower() and f.endswith('.dbf'):
            in_dbf = os.path.join(cwd, root, f)
            out_dbf = os.path.basename(os.path.dirname(root))
            out_dbf = os.path.join(cwd, hydroGDB, 'Velocity_' + out_dbf[7:])
            arcpy.CopyRows_management(in_dbf, out_dbf)
        if 'flowline' in f.lower() and f.endswith('.shp'):
            in_shp = os.path.join(cwd, root, f)
            out_shp = os.path.basename(os.path.dirname(os.path.dirname(root)))
            out_shp = os.path.join(cwd, hydroGDB, 'Flowline_' + out_shp[7:])
            arcpy.CopyFeatures_management(in_shp, out_shp)

# join velocity information (in the tables) to the flowline feature class; per VPU:

for table in arcpy.ListTables():
    vpu = table[9:]  # extract VPU number from the table name

    arcpy.MakeFeatureLayer_management(in_features='Flowline_' + vpu,
                                      out_layer='NHD_flowline_' + vpu,
                                      workspace=arcpy.env.scratchWorkspace)

    arcpy.MakeTableView_management(in_table=table,
                                   out_view='NHD_velocity_' + vpu,
                                   where_clause='"MAVELV" > -9999',
                                   workspace=arcpy.env.scratchWorkspace)

    joined_table = arcpy.AddJoin_management('NHD_flowline_' + vpu, 'COMID',
                                            'NHD_velocity_' + vpu, 'COMID',
                                            join_type='KEEP_COMMON')
    # Copy the layer to a new permanent feature class
    arcpy.CopyFeatures_management(joined_table, 'FlowPlusVelo_' + vpu)

###############
# 3. Analysis #
###############

# (a) combine the 3 hydro regions into a single feature class using cursors:

arcpy.ClearEnvironment('scratchWorkspace')  # without this there is a memory error trying to calculate slope!
sr = arcpy.Describe('FlowPlusVelo_07').spatialReference  # extract spatial reference
fields = ['COMID', 'MAVELV']
arcpy.CreateFeatureclass_management(os.path.join(cwd, hydroGDB), 'AllVelocities', 'POLYLINE', spatial_reference=sr)
arcpy.management.AddField('AllVelocities', fields[0], 'LONG')
arcpy.management.AddField('AllVelocities', fields[1], 'FLOAT')
icursor = arcpy.da.InsertCursor('AllVelocities',  ['OID@', 'SHAPE@']+fields)
for fc in ['FlowPlusVelo_07', 'FlowPlusVelo_10U', 'FlowPlusVelo_10L']:
    fieldnames = [f.name for f in arcpy.ListFields(fc)]
    scursor = arcpy.da.SearchCursor(fc, ['OID@', 'SHAPE@', fieldnames[2], fieldnames[-1]])
    for row in scursor:
        to_insert = (row[0], row[1], row[2], row[-1]) #(row.getValue(fieldnames[2]), row.getValue(fieldnames[-2]))
        icursor.insertRow(to_insert)
    del scursor  # delete search cursor
del icursor  # delete insert cursor

# (b) convert cumulative feature class to raster, with values of velocity:

arcpy.FeatureToRaster_conversion('AllVelocities', 'MAVELV', 'AllVel_Raster', 0.001)

# (c) calculate the slope for each county raster:

arcpy.env.workspace = os.path.join(cwd, 'data', 'DEM')

county_rasters = arcpy.ListRasters() # get a list of raster files (per county) making up the state of Iowa

for in_raster in county_rasters:  # NOTE: I had to run the 'slope' tool manually on ArcMap for DEM_3m_I_69.img
    print q  # 999999 error after 68
    slope = arcpy.sa.Slope(in_raster, 'PERCENT_RISE', z_factor=0.01)
    out_name = 'slope_'+in_raster.split('.')[0][-2:]
    #print(out_name)
    slope.save(os.path.join(cwd, hydroGDB, out_name))

# (d) Calculate the ratio of velocity-0.094 over slope^0.159 (per county raster)

diff = arcpy.sa.Raster('AllVel_Raster') - 0.094
diff = arcpy.sa.Con(diff>0, diff)  # to avoid negatives and (later) div by zero
diff.save('Vel_minus_bias')
'''
arcpy.ClearEnvironment('scratchWorkspace')  # without this there is a memory error trying to calculate slope!

slope_rasters = [raster for raster in arcpy.ListRasters() if 'slope' in raster]

for slope in slope_rasters[35:]: # NOTE: 17, 35 threw errors...
    ratio = arcpy.sa.Raster('Vel_minus_bias') / arcpy.sa.Power(arcpy.sa.Raster(slope), 0.159)
    ratio.save('ratio_'+slope[-2:])

# (e) Extract values from rasters to arrays, concatenate arrays and plot relationships
# https://gis.stackexchange.com/questions/303865/accessing-raster-values-to-create-histogram-using-arcpy

ratio_rasters = [raster for raster in arcpy.ListRasters() if 'ratio' in raster]
all_ratios = []

for ratio in ratio_rasters:
    array = arcpy.RasterToNumPyArray(ratio)
    for elmt in array:
        all_ratios.append(elmt)

print len(all_ratios)
#arcpy.env.workspace = cwd  # restore workspace to cwd

################
# -1. Clean-up #
################

arcpy.CheckInExtension('Spatial')  # check in Spatial Analyst extension

# average raster value along polyline
# (https://gis.stackexchange.com/questions/174367/extracting-raster-values-to-polyline-feature)

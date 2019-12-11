# Author:   Marios Tsekitsidis
# Date:     December 10, 2019
# Version:  Python 3.7
# Purpose:  This script was written as part of the Final Project in C R P 556 (F19)


from tqdm import tqdm
import requests
import os


''' 1. Download raw DEM data (.zip files) '''

# Parameters for request to Box API:
dev_token = ''  # requires box dev application (expires every hr)
shared_folder_url = 'https://iastate.box.com/s/dboob8jvve6qvk639smhbpsw0b7g4qbf'  # ISU GIS Facility Pub folder
headers = {'Authorization': 'Bearer ' + dev_token, 'BoxApi': 'shared_link=' + shared_folder_url}  # request headers


# Function to download DEM data:
def download_dem():
    os.mkdir('Counties_DEM_raw')  # create new directory to download data into
    os.chdir('Counties_DEM_raw')  # set new directory as current directory
    try:
        # Get list of counties, i.e. items (subdirectories) in the 'Counties' directory:
        response = requests.get('https://api.box.com/2.0/folders/52245723277/items', headers=headers)  # send request
        as_dict = response.json()  # capture request as a dictionary

        # Save county info in list of (id, name) tuples:
        counties = [(county['id'], county['name']) for county in as_dict['entries']]

        # For each county, find and download DEM data file (zip):
        for county in tqdm(counties, 'Downloading counties DEM...'):
            county_id, county_name = county  # extract id, name as different variables
            os.mkdir(county_name)  # create county-specific directory
            os.chdir(county_name)  # set county-specific directory as current directory
            try:
                data_items = requests.get('https://api.box.com/2.0/folders/'+county_id+'/items', headers=headers)
                as_dict = data_items.json()
                dem_file = None  # tuple to hold DEM file info
                # For each item (file/folder) in the county folder:
                for item in as_dict['entries']:
                    # If the item's filename contains the strings "DEM" and ".zip":
                    if 'DEM' in item['name'] and '.zip' in item['name']:
                        dem_file = (item['id'], item['name'])  # store file info
                        break  # stop searching
                if dem_file:  # if DEM data found
                    try:
                        # Download DEM data:
                        dem_raw = requests.get('https://api.box.com/2.0/files/'+dem_file[0]+'/content', headers=headers)
                        with open(dem_file[1], 'wb') as f:
                            f.write(dem_raw.content)
                    except requests.exceptions.RequestException:
                        print('Could not download DEM data for ' + county_name + ' county!')
                else:
                    print('No DEM data found for '+county_name+' county!')
            except requests.exceptions.RequestException:
                print('Could not access '+county_name+' county folder!')
            os.chdir('..')
    except requests.exceptions.RequestException as e:
        print(e)  # print encountered error
    os.chdir('..')


# Call function to download DEM data:
download_dem()

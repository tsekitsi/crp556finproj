# Author:   Marios Tsekitsidis
# Date:     December 16, 2019
# Version:  Python 2.7.13
# Purpose:  This script was written as part of the Final Project in C R P 556 (F19)


import requests


class BoxWalker:
    # parameters for request to Box API:
    dev_token = None  # requires box dev application (expires every hr)
    shared_folder_url = None  # shared folder to walk
    headers = None  # headers to be used in GET request
    discovered = set()  # for Depth First Search
    files = {}  # for Depth First Search

    def __init__(self, shared_folder_url, dev_token):
        self.dev_token = dev_token
        self.shared_folder_url = shared_folder_url
        self.headers = {'Authorization': 'Bearer ' + self.dev_token,
                        'BoxApi': 'shared_link=' + self.shared_folder_url}

    # function 'get_items' returns two lists; one with IDs of sub-folders and one with IDs of files in folder:
    def get_items(self, folder_id):
        folders = []
        files = []
        items = requests.get('https://api.box.com/2.0/folders/' + folder_id + '/items', headers=self.headers)
        as_dict = items.json()
        # for each item (file/folder) in the folder:
        for item in as_dict['entries']:
            if item['type'] == 'folder':
                folders.append(item['id'])
            if item['type'] == 'file':
                files.append((item['id'], item['name']))
        return folders, files

    def dfs(self, folder_id, filters):
        # print 'now in folder ' + folder_id  # TO-DO: convert to logger
        self.discovered.add(folder_id)
        new_folders, new_files = self.get_items(folder_id)
        for nf in new_files:
            if filters:
                if filters['contains'] in nf[1] and nf[1].endswith(filters['endswith']):
                    self.files[nf[0]] = nf[1]
            else:
                self.files[nf[0]] = nf[1]
        for sub_dir in new_folders:
            if sub_dir not in self.discovered:
                self.dfs(sub_dir, filters)

    def walk(self, folder_id, filters=None):
        print '  Walking folder ' + folder_id + '...',
        self.dfs(folder_id, filters)
        print 'Done!'
        return [(id_, name) for id_, name in self.files.items()]

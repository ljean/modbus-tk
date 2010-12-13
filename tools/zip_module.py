#!/usr/bin/env python
# -*- coding: utf_8 -*-
#
# Modbus TestKit: Implementation of Modbus protocol in python
#
# (C)2009 - Luc Jean - luc.jean@gmail.com
# (C)2009 - Apidev - http://www.apidev.fr
#
# This is distributed under GNU LGPL license, see license.txt
#

import zipfile
import glob, os, sys

class ZipArchive:

    def zip_it(self, dirName, files):
        dirNamePrefix = dirName+"/*"
        for filename in glob.glob(dirNamePrefix):
            if os.path.isfile(filename):
                exclude_me = False
                for exclude in self.exclude_list:
                    if filename.find(exclude)!=-1:
                        exclude_me = True
                        break
                if not exclude_me:
                    print filename
                    name = filename[len(self.folder)+1:]
                    self.archive.write(filename, name, zipfile.ZIP_DEFLATED)
        
    def run(self, folder, name):
        self.exclude_list = (".svn", ".pyc", "build", "tools", "release", ".egg-info",
             "dist", ".externalTool", ".settings", ".hg")
        self.folder = folder
        self.archive = zipfile.ZipFile(name+".zip", "w")
        os.path.walk(self.folder, ZipArchive.zip_it, self)
        self.archive.close()
        
if __name__ == "__main__":
    arch = ZipArchive()
    old_dir = os.getcwd()
    wkdir = os.path.abspath(os.path.dirname(sys.argv[0])+"\\..")
    os.chdir(wkdir+"\\tools")
    arch.run(wkdir, "modbus-tk")
    os.chdir(old_dir)
    print "done"

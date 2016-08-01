# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Image Footprint
Description          : Plugin for create a catalog layer from directories of images
Date                 : July, 2016
copyright            : (C) 2016 by Luiz Motta
email                : motta.luiz@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os

from PyQt4 import QtCore
from qgis import gui as QgsGui

from processtemplate import WorkerTemplate, MessageBarTemplate, ProcessTemplate

from osgeo import gdal
from gdalconst import GA_ReadOnly
gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

class WorkerValidImages(WorkerTemplate):
  def __init__(self):
    super(WorkerValidImages, self).__init__()
    self.images = None

  def setData(self, data):
    self.images = data['images']
    self.dirImages = data['dirImages']
    self.hasSubDir = data['hasSubDir']
    self.filters = data['filters']
    self.hasInverse = data['hasInverse']

  @QtCore.pyqtSlot()
  def run(self):
    def getValids(root, files):
      def addImage(root, file):
        def validDataSet(filename):
          ds = None
          try:
            ds = gdal.Open( filename, GA_ReadOnly )            
          except RuntimeError:
            pass
          not_valid = ds is None or len( ds.GetProjectionRef() ) == 0 or ds.RasterCount == 0
          return None if not_valid else ds

        filename = os.path.join( root, file )
        ds = validDataSet( filename )
        if ds is None:
          return
        ds = None
        images.append( filename )
        
      filters = None
      hasFilters = len( self.filters ) > 0
      if hasFilters:
        filters = self.filters.upper().split(',')
      images = []
      if hasFilters:
        if self.hasInverse:
          for i in xrange( len( files ) ):
            file = files[ i ]
            if not any( w in file.upper() for w in filters ):
              addImage( root, file )
        else:
          for i in xrange( len( files ) ):
            file = files[ i ]
            if any( w in file.upper() for w in filters ):
              addImage( root, file )
      else:
        for i in xrange( len( files ) ):
          addImage( root, files[ i ] )

      return images
    
    if self.hasSubDir:
      for root, dirs, files in os.walk( self.dirImages ):
        if self.isKilled:
          break
        self.images.extend( getValids( root, files ) )
    else:
      for root, dirs, files in os.walk( self.dirImages ):
        if self.isKilled:
          break
        self.images.extend( getValids( root, files ) )
        break

    self.finished.emit({})

class MessageBarCancel(MessageBarTemplate):
  def __init__(self, pluginName, msg):
    super(MessageBarCancel, self).__init__( pluginName, msg, [ WorkerValidImages ] )

class ValidImages(ProcessTemplate):
  def __init__(self, pluginName,  nameModulus):
    super(ValidImages, self).__init__( pluginName,  nameModulus, WorkerValidImages )

  def run(self, dataDlgFootprint, images):
    self.msgBar.clearWidgets()
    data = {
      'images': images,
      'dirImages': dataDlgFootprint['dirImages'],
      'hasSubDir': dataDlgFootprint['hasSubDir'] ,
      'filters': dataDlgFootprint['filters'] ,
      'hasInverse': dataDlgFootprint['hasInverse']
    }
    msg = " and its subdirectories" if data['hasSubDir'] else ""
    d = ( data['dirImages'], msg )
    msg = "Searching images in '%s'%s..." % d
    self.mb = MessageBarCancel( self.pluginName, msg )
    self.msgBar.pushWidget( self.mb.msgBarItem, QgsGui.QgsMessageBar.INFO )
    
    self.worker.setData( data )
    WorkerValidImages.isKilled = False
    self.thread.start()
    #self.worker.run() # DEBUG

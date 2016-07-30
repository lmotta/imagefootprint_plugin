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

from PyQt4 import ( QtCore, QtGui )
from qgis import ( gui as QgsGui, utils as QgsUtils )

from osgeo import gdal
from gdalconst import GA_ReadOnly
gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

class WorkerValidImages(QtCore.QObject):
  finished = QtCore.pyqtSignal()
  isKilled = False

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

    self.finished.emit()

class MessageBarCancel(QtCore.QObject):
  def __init__(self, pluginName, msg ):
    def initGui():
      def setCancel():
        self.tbCancel.setIcon( QtGui.QIcon(":/images/themes/default/mActionFileExit.png") )
        self.tbCancel.setText( "Cancel")
        self.tbCancel.setToolButtonStyle( QtCore.Qt.ToolButtonTextBesideIcon )

      self.msgBarItem = QgsUtils.iface.messageBar().createMessage( pluginName, msg )
      self.tbCancel = QtGui.QToolButton( self.msgBarItem )
      setCancel()
      lyt = self.msgBarItem.layout()
      lyt.addWidget( self.tbCancel )

    super(MessageBarCancel, self).__init__()
    self.msgBarItem = self.tbCancel = None
    initGui()
    self.tbCancel.clicked.connect( self.clickedCancel )
    
  @QtCore.pyqtSlot(bool)
  def clickedCancel(self, checked):
    WorkerValidImages.isKilled = True
    self.tbCancel.setEnabled( False )

class ValidImages(QtCore.QObject):
  finished = QtCore.pyqtSignal()
  
  def __init__(self, pluginName, nameModulus):
    super(ValidImages, self).__init__()
    self.pluginName, self.nameModulus = pluginName, nameModulus
    self.worker = self.thread = self.mbp = None
    self.msgBar = QgsUtils.iface.messageBar()
    self.initThread()
    
  def __del__(self):
    self.finishThread()

  def initThread(self):
    self.worker = WorkerValidImages()
    self.thread = QtCore.QThread( self )
    self.thread.setObjectName( self.nameModulus )
    self.worker.moveToThread( self.thread )
    self._connectWorker()

  def finishThread(self):
    self._connectWorker( False )
    self.worker.deleteLater()
    self.thread.wait()
    self.thread.deleteLater()
    self.thread = self.worker = None

  def _connectWorker(self, isConnect = True):
    ss = [
      { 'signal': self.thread.started,   'slot': self.worker.run },
      { 'signal': self.worker.finished,  'slot': self.finishedWorker }
    ]
    if isConnect:
      for item in ss:
        item['signal'].connect( item['slot'] )  
    else:
      for item in ss:
        item['signal'].disconnect( item['slot'] )

  @QtCore.pyqtSlot()
  def finishedWorker(self):
    self.thread.quit()
    self.finished.emit()

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
    self.mbc = MessageBarCancel( self.pluginName, msg )
    self.msgBar.pushWidget( self.mbc.msgBarItem, QgsGui.QgsMessageBar.INFO )
    
    self.worker.setData( data )
    WorkerValidImages.isKilled = False
    self.thread.start()
    #self.worker.run() # DEBUG

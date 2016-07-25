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
import os, stat, sys, re, shutil, filecmp

from PyQt4 import ( QtGui, QtCore )

from imagefootprint import ( DialogFootprint, CatalogFootprint )

def classFactory(iface):
  return ImageFootprintPlugin( iface )

class ImageFootprintPlugin:
  def __init__(self, iface):
    self.iface = iface
    self.namePlugin = u"Image &Footprint"
    self.action = None
    CatalogFootprint.copyExpression()
    self.catalog = CatalogFootprint( self.namePlugin.replace('&', '') )
    self.dlgFootprint = None

  def initGui(self):

    name = self.namePlugin.replace('&', '')
    about = "Create a catalog layer from directories of images"
    icon = QtGui.QIcon( os.path.join( os.path.dirname(__file__), 'imagefootprint.svg' ) )
    self.action = QtGui.QAction( icon, name, self.iface.mainWindow() )
    self.action.setObjectName( name.replace(' ', '') )
    self.action.setWhatsThis( about )
    self.action.setStatusTip( about )
    #self.action.setCheckable( True )
    self.action.triggered.connect( self.run )

    self.iface.addToolBarIcon( self.action )
    self.iface.addPluginToMenu( self.namePlugin, self.action)

  def unload(self):
    self.iface.removeToolBarIcon( self.action )
    self.iface.removePluginMenu( self.namePlugin, self.action)
    del self.action

  @QtCore.pyqtSlot()
  def run(self):
    if self.dlgFootprint is None:
      self.dlgFootprint = DialogFootprint( self.namePlugin.replace('&', '') )
      self.dlgFootprint.show()
      self.dlgFootprint.setFixedSize( self.dlgFootprint.size() )
      self.dlgFootprint.hide()

    if self.dlgFootprint.isVisible():
      self.dlgFootprint.activateWindow()
      return

    if self.dlgFootprint.exec_() == QtGui.QDialog.Accepted:
      data = {
        'dirImages': self.dlgFootprint.dirImages,
        'filters': self.dlgFootprint.textFilters,
        'hasInverse': self.dlgFootprint.hasInverse,
        'wktCrsImages': self.dlgFootprint.wktCrsImages,
        'hasValidPixels': self.dlgFootprint.hasValidPixels,
        'hasSubDir': self.dlgFootprint.hasSubDir
      }
      self.catalog.run( data )

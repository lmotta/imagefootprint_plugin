# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Image Footprint
Description          : Plugin for create a catalog layer from directories of images
Date                 : July, 2016, At January, 2019 migrate for processing framework
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

__author__ = 'Luiz Motta'
__date__ = '2016-07-24'
__copyright__ = '(C) 2016, Luiz Motta'
__revision__ = '$Format:%H$'


import os

from qgis.PyQt.QtCore import QObject, QCoreApplication, pyqtSlot
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsApplication
import processing # QGIS Processing

from .translate import Translate


def classFactory(iface):
  return ImageFootprintPlugin( iface )

class ImageFootprintPlugin(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.namePlugin = u"Image &Footprint"
        self.action = None
        self.translate = Translate('imagefootprint')

    def initGui(self):
        name = self.namePlugin.replace('&', '')
        about = "Create a catalog layer from directories of images"
        icon = QIcon( os.path.join( os.path.dirname(__file__), 'footprint.svg' ) )
        self.action = QAction( icon, name, self.iface.mainWindow() )
        self.action.setObjectName( name.replace(' ', '') )
        self.action.setWhatsThis( about )
        self.action.setStatusTip( about )
        self.action.triggered.connect( self.run )

        self.iface.addToolBarIcon( self.action )
        self.iface.addPluginToRasterMenu( self.namePlugin, self.action )

    def unload(self):
        self.iface.removeToolBarIcon( self.action )
        self.iface.removePluginRasterMenu( self.namePlugin, self.action)
        del self.action

    @pyqtSlot(bool)
    def run(self, checked):
        algorith = QgsApplication.processingRegistry().algorithmById ('ibama:Footprint')
        if algorith is None:
            title = self.namePlugin.replace('&', '')
            msg = QCoreApplication.translate('Footprint', 'This plugin NEED the install IBAMA processing plugin.')
            self.iface.messageBar().pushCritical ( title, msg )
            return
        processing.createAlgorithmDialog( algorith ).show()

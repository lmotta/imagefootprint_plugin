# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Class MessageBarProgress
Description          : Class for show progress in Message Bar
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
 *                                  messageBar                                       *
 ***************************************************************************/
"""
from PyQt4 import ( QtGui, QtCore )
from qgis import ( gui as QgsGui, utils as QgsUtils )


class MessageBarProgress(QtCore.QObject):
  canceled = QtCore.pyqtSignal()
  
  def __init__(self, pluginName, title, maximum):
    def initGui():
      def setCancel():
        self.tbCancel.setIcon( QtGui.QIcon(":/images/themes/default/mActionFileExit.png") )
        self.tbCancel.setText( "Cancel")
        self.tbCancel.setToolButtonStyle( QtCore.Qt.ToolButtonTextBesideIcon )

      self.pb = QtGui.QProgressBar( msgBar )
      self.pb.setAlignment( QtCore.Qt.AlignLeft )
      self.tbCancel = QtGui.QToolButton( msgBar )
      setCancel()
      msg = "%s - %d images" % ( title, maximum  )
      self.widget = msgBar.createMessage( pluginName, msg )
      lyt = self.widget.layout()
      lyt.addWidget( self.tbCancel )
      lyt.addWidget( self.pb )

    super(MessageBarProgress, self).__init__()
    self.widget = self.pb = self.tbCancel = None
    msgBar = QgsUtils.iface.messageBar()
    initGui()
    self.tbCancel.clicked.connect( self.clickedCancel )
    self.pb.setValue( 1 )
    self.pb.setMaximum( maximum )
    msgBar.pushWidget( self.widget, QgsGui.QgsMessageBar.INFO )

  def step(self, value):
    self.pb.setValue( value )

  @QtCore.pyqtSlot(bool)
  def clickedCancel(self, checked):
    self.canceled.emit()
    self.tbCancel.clicked.disconnect( self.clickedCancel )


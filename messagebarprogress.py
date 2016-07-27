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
  def __init__(self, pluginName, msg, funcKill):
    def initGui():
      def setCancel():
        self.tbCancel.setIcon( QtGui.QIcon(":/images/themes/default/mActionFileExit.png") )
        self.tbCancel.setText( "Cancel")
        self.tbCancel.setToolButtonStyle( QtCore.Qt.ToolButtonTextBesideIcon )

      self.msgBarItem = QgsUtils.iface.messageBar().createMessage( pluginName, msg )
      self.pb = QtGui.QProgressBar( self.msgBarItem )
      self.pb.setAlignment( QtCore.Qt.AlignLeft )
      self.tbCancel = QtGui.QToolButton( self.msgBarItem )
      setCancel()
      
      lyt = self.msgBarItem.layout()
      lyt.addWidget( self.tbCancel )
      lyt.addWidget( self.pb )

    super(MessageBarProgress, self).__init__()
    self.funcKill = funcKill
    self.msgBarItem = self.pb = self.tbCancel = None
    initGui()
    self.tbCancel.clicked.connect( self.clickedCancel )
    
  def init(self, maximum):
    self.pb.setValue( 0 )
    self.pb.setMaximum( maximum )
    self.msgBarItem.setText( "Total %d" % maximum )
  
  def step(self, step):
    value = self.pb.value() + step 
    self.pb.setValue( value )

  @QtCore.pyqtSlot(bool)
  def clickedCancel(self, checked):
    self.funcKill()
    self.tbCancel.setEnabled( False )



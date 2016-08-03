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
from qgis import core as QgsCore
from imagefootprint_plugin import CatalogFootprint

@QgsCore.qgsfunction(args=1, group='Image Footprint')
def getValueFromMetadataFootprint(values, feature, parent):
  """
  <h4>Return</h4>Get value of key of 'data_json' field
  <p><h4>Syntax</h4>getValueFromMetadataFootprint('list_keys')</p>
  <p><h4>Argument</h4>list_keys -> String with a sequence of keys names</p>
  <p><h4>Example</h4>getValueFromMetadataFootprint( 'crs,description' )</p><p>Return: Description of CRS</p>
  """
  def getIdField(name):
    id = feature.fieldNameIndex( name )
    if id == -1:
      raise Exception("Error! Need have '%s' field." % name )
    return id

  if len( values[0] ) < 1:
    raise Exception("Error! Field is empty." )

  meta_json = feature.attributes()[ getIdField( 'meta_json' ) ]
  lstKey = map( lambda item: item.strip(), values[ 0 ].split(",") )
  try:
    ( success, valueKey) = CatalogFootprint.getValueMetadata( meta_json, lstKey )
  except:
    raise Exception("Error read arguments.")

  if not success:
    raise Exception( valueKey )

  return valueKey

@QgsCore.qgsfunction(args=1, group='Image Footprint')
def getDirName(values, feature, parent):
  """
  <h4>Return</h4>Get the name diretory of file name
  <p><h4>Syntax</h4>getDirName('filename')</p>
  <p><h4>Argument</h4>filename -> String with path and name of file</p>
  <p><h4>Example</h4>getDirName( '/home/lmotta/temp/test.tif' )</p><p>Return: '/home/lmotta/temp'</p>
  """
  return os.path.dirname( values[0] )

@QgsCore.qgsfunction(args=1, group='Image Footprint')
def getDateLandsat(values, feature, parent):
  """
  <h4>Return</h4>QDate from file name of Landsat
  <p><h4>Syntax</h4>getDateLandsat(name_landsat)</p>
  <p><h4>Argument</h4>name_landsat -> name file of Landsat</p>
  <p><h4>Example</h4>getDateLandsat('LC81390452014295LGN00')-> QDate(2014, 10, 22)</p>
  """
  try:
    julianYear = QtCore.QDate( int( values[0][9:13] ), 1, 1 ).toJulianDay() - 1
    julianDays = julianYear + int( values[0][13:16] )
    v_date = QtCore.QDate.fromJulianDay ( julianDays )
  except:
    raise Exception("Enter with landsat 8 name (ex. 'LC81390452014295LGN00').")
    return QtCore.QDate()
  #
  return v_date

@QgsCore.qgsfunction(args=1, group='Image Footprint')
def getDateRapideye(values, feature, parent):
  """
  <h4>Return</h4>QDate from file name of Rapideye
  <p><h4>Syntax</h4>getDateRapideye(name_rapideye)</p>
  <p><h4>Argument</h4>name_rapideye -> name file of Rapideye</p>
  <p><h4>Example</h4>getDateRapideye('2227625_2012-12-26T142009_RE1_3A-NAC_14473192_171826')-> QDate(2012, 12, 26)</p>
  """
  try:
    v_date = QtCore.QDate.fromString( values[0].split('_')[1][:10], "yyyy-MM-dd" )
  except:
    raise Exception("Enter with Rapideye name (ex. '2227625_2012-12-26T142009_RE1_3A-NAC_14473192_171826'). Value error = %s" % values[0])
    return QtCore.QDate()
  #
  return v_date

@QgsCore.qgsfunction(args=1, group='Image Footprint')
def getDatePlanetlabs(values, feature, parent):
  """
  <h4>Return</h4>QDate from file name of Planetlabs
  <p><h4>Syntax</h4>getDatePlanetlabs(name_planetlabs)</p>
  <p><h4>Argument</h4>name_planetlabs -> name file of Planetlabs</p>
  <p><h4>Example</h4>getDatePlanetlabs('20151109_182728_1_0b0a_analytic.tif')-> QDate(2015, 11, 09)</p>
  """
  try:
    v_date = QtCore.QDate.fromString( values[0].split('_')[0], "yyyyMMdd" )
  except:
    raise Exception("Enter with Planetlabs name (ex. '20151109_182728_1_0b0a_analytic'). Value error = %s" % values[0])
    return QtCore.QDate()
  #
  return v_date

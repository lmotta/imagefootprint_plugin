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
  return os.path.dirname( values[0] )

    
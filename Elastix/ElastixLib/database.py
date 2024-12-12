import qt
import vtk

import abc
import os
import slicer
from pathlib import Path
from ElastixLib.preset import createPreset

"""

database could be
  builtin
  custom (user directory)
  in scene
    scan scene for scripted nodes
  
  each database needs to implement its interface on how to retrieve the data
  

"""


class ElastixDatabase(abc.ABC):

  # @staticmethod
  # def getRegistrationPresetsFromXML(elastixParameterSetDatabasePath):
  #   if not os.path.isfile(elastixParameterSetDatabasePath):
  #     raise ValueError("Failed to open parameter set database: " + elastixParameterSetDatabasePath)
  #   elastixParameterSetDatabaseXml = vtk.vtkXMLUtilities.ReadElementFromFile(elastixParameterSetDatabasePath)
  #
  #   # Create python list from XML for convenience
  #   registrationPresets = []
  #   for parameterSetIndex in range(elastixParameterSetDatabaseXml.GetNumberOfNestedElements()):
  #     parameterSetXml = elastixParameterSetDatabaseXml.GetNestedElement(parameterSetIndex)
  #     parameterFilesXml = parameterSetXml.FindNestedElementWithName('ParameterFiles')
  #     parameterFiles = []
  #     for parameterFileIndex in range(parameterFilesXml.GetNumberOfNestedElements()):
  #       parameterFiles.append(parameterFilesXml.GetNestedElement(parameterFileIndex).GetAttribute('Name'))
  #     parameterSetAttributes = \
  #       [parameterSetXml.GetAttribute(attr) for attr in ['id', 'modality', 'content', 'description', 'publications']]
  #     registrationPresets.append(parameterSetAttributes + [parameterFiles])
  #   return registrationPresets

  def getRegistrationPresetsFromXML(self, elastixParameterSetDatabasePath):
    if not os.path.isfile(elastixParameterSetDatabasePath):
      raise ValueError("Failed to open parameter set database: " + elastixParameterSetDatabasePath)
    elastixParameterSetDatabaseXml = vtk.vtkXMLUtilities.ReadElementFromFile(elastixParameterSetDatabasePath)

    # Create python list from XML for convenience
    registrationPresets = []
    for parameterSetIndex in range(elastixParameterSetDatabaseXml.GetNumberOfNestedElements()):
      parameterSetXml = elastixParameterSetDatabaseXml.GetNestedElement(parameterSetIndex)
      parameterFilesXml = parameterSetXml.FindNestedElementWithName('ParameterFiles')
      parameterFiles = []
      for parameterFileIndex in range(parameterFilesXml.GetNumberOfNestedElements()):
        parameterFiles.append(os.path.join(
          str(Path(elastixParameterSetDatabasePath).parent),
          parameterFilesXml.GetNestedElement(parameterFileIndex).GetAttribute('Name'))
        )
      parameterSetAttributes = \
        [parameterSetXml.GetAttribute(attr) for attr in ['id', 'modality', 'content', 'description', 'publications']]
      registrationPresets.append(
        createPreset(*parameterSetAttributes, parameterFiles=parameterFiles, inScene=False)
      )
    return registrationPresets


  def __init__(self):
    self.registrationPresets = None

  def getRegistrationPresets(self, force_refresh=False):
    # TODO: need to check scene for any loaded presets?
    # TODO: when keeping in the scene, probably a good idea to have a parameter node or such that references text nodes?
    #       or could also think about a folder / scripted node

    if self.registrationPresets and not force_refresh:
      return self.registrationPresets

    self.registrationPresets = self._getRegistrationPresets()

    return self.registrationPresets


  @abc.abstractmethod
  def _getRegistrationPresets(self):
    pass


class BuiltinElastixDatabase(ElastixDatabase):

  # load txt files into slicer scene
  DATABASE_FILE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Resources', 'RegistrationParameters',
                 'ElastixParameterSetDatabase.xml'))

  def getPresetsDir(self):
    return str(Path(self.DATABASE_FILE).parent)

  # handling things like listing, cloning, creating, modifying ...
  # TODO: could also have signals for the widget to connect to?

  def overwriteParFile(self, filename):
    # TODO: overwrite not allowed
    d = qt.QDialog()
    resp = qt.QMessageBox.warning(d, "Overwrite File?",
                                  "File \"%s\" already exists and is not identical, do you want to overwrite it? (Clicking Discard would exclude the file from the preset)" % filename,
                                  qt.QMessageBox.Save | qt.QMessageBox.Discard | qt.QMessageBox.Abort,
                                  qt.QMessageBox.Save)
    return resp == qt.QMessageBox.Save

  def _getRegistrationPresets(self):
    return self.getRegistrationPresetsFromXML(self.DATABASE_FILE)



class UserElastixDataBase(ElastixDatabase):

  DATABASE_LOCATION = Path(slicer.app.slicerUserSettingsFilePath).parent / "Elastix"

  @staticmethod
  def getAllXMLFiles(directory):
    import fnmatch
    files = []
    for root, dirnames, filenames in os.walk(directory):
      for filename in fnmatch.filter(filenames, '*{}'.format(".xml")):
        files.append(os.path.join(root, filename))
    return files

  def __init__(self):
    self.DATABASE_LOCATION.mkdir(exist_ok=True)
    super().__init__()

  def getPresetsDir(self):
    return self.DATABASE_LOCATION

  def _getRegistrationPresets(self):
    xml_files = self.getAllXMLFiles(self.DATABASE_LOCATION)
    registrationPresets = []
    for xml_file in xml_files:
      registrationPresets.extend(self.getRegistrationPresetsFromXML(xml_file))
    return registrationPresets

  # def createPreset(self, dialog):
  #   # create folder in db
  #   # create xml
  #   # copy txt files
  #
  #   filenames = dialog.getParameterFiles()
  #   if len(filenames) > 0:
  #     from shutil import copyfile
  #     import xml.etree.ElementTree as ET
  #     presetDatabase = self.logic.databaseFile
  #     xml = ET.parse(presetDatabase)
  #     root = xml.getroot()
  #     attributes = dialog.getMetaInformation()
  #
  #     presetElement = ET.SubElement(root, "ParameterSet", attributes)
  #     parFilesElement = ET.SubElement(presetElement, "ParameterFiles")
  #
  #     # Copy parameter files to database directory
  #     for file in filenames:
  #       filename = os.path.basename(file)
  #       newFilePath = os.path.join(folder, filename)
  #       createFileCopy = True
  #       discard = False
  #       if os.path.exists(newFilePath):
  #         import hashlib
  #         # check if identical
  #         if hashlib.md5(open(newFilePath, 'rb').read()).hexdigest() == hashlib.md5(open(file, 'rb').read()).hexdigest():
  #           createFileCopy = False
  #         else: # not identical but same name
  #           if self.overwriteParFile(filename):
  #             createFileCopy = True
  #           else:
  #             discard = True
  #       if createFileCopy:
  #         copyfile(file, newFilePath)
  #       if not discard:
  #         ET.SubElement(parFilesElement, "File", {"Name": filename})
  #
  #     xml.write(presetDatabase)


class InSceneElastixDatabase(ElastixDatabase):

  def _getRegistrationPresets(self):
    registrationPresets = []

    nodes = filter(lambda node: node.GetAttribute('Type') == 'ElastixPreset',
           slicer.util.getNodesByClass('vtkMRMLScriptedModuleNode'))

    from ElastixLib.preset import getInScenePreset
    for node in nodes:
      registrationPresets.append(getInScenePreset(node))


    return registrationPresets

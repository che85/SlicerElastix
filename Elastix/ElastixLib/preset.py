import os.path

import slicer
from typing import List, Union

# for caching instead of persistently creating new preset for each node in the scene
InScenePresets = {}

"""

preset base provides an interface that needs to be implemented for in storage presets and in scene presets
"""

# search current scene for in scene presets

from abc import ABC, abstractmethod

class PresetBase(ABC):

  @abstractmethod
  def setID(self, value: str):
    pass

  @abstractmethod
  def getID(self) -> str:
    pass

  @abstractmethod
  def setModality(self, value: str):
    pass

  @abstractmethod
  def getModality(self):
    pass

  @abstractmethod
  def setContent(self, value: str):
    pass

  @abstractmethod
  def getContent(self) -> str:
    pass

  @abstractmethod
  def setDescription(self, value: str):
    pass

  @abstractmethod
  def getDescription(self) -> str:
    pass

  @abstractmethod
  def setPublications(self, value: str):
    pass

  @abstractmethod
  def getPublications(self) -> str:
    pass

  @abstractmethod
  def setParameterFiles(self, value: List):
    pass

  @abstractmethod
  def getParameterFiles(self) -> List:
    pass

  @abstractmethod
  def addParameterFile(self, value):
    pass


class Preset(PresetBase):

  def setID(self, value):
    self._id = value

  def getID(self):
    return self._id

  def setModality(self, value: str):
    self._modality = value

  def getModality(self):
    return self._modality

  def setContent(self, value: str):
    self._content = value

  def getContent(self) -> str:
    return self._content

  def setDescription(self, value: str):
    self._description = value

  def getDescription(self) -> str:
    return self._description

  def setPublications(self, value: str):
    self._publications = value

  def getPublications(self) -> str:
    return self._publications

  def setParameterFiles(self, value: List):
    if type(value) is str:
      raise ValueError("Parameter files parameter needs to be a list of file paths")
    self._parameterFiles = value

  def getParameterFiles(self) -> List:
    return self._parameterFiles

  def addParameterFile(self, value):
    self._parameterFiles.append(value)

  def __init__(self):
    self._id = ""
    self._modality = ""
    self._description = ""
    self._content = ""
    self._publications = ""
    self._parameterFiles = []


class InScenePreset(PresetBase):

  @staticmethod
  def createPresetNode():
    presetNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode")
    presetNode.SetAttribute("Type", "ElastixPreset")
    return presetNode



  def __init__(self, presetNode: slicer.vtkMRMLScriptedModuleNode = None):
    """ Creates new scripted node if none was defined

    :param presetNode:
    """
    self._presetNode = None
    self.setPresetNode(presetNode)
    if not self._presetNode:
      node = self.createPresetNode()
      self.setPresetNode(node)

  def delete(self):
    nodes = self.getParameterFiles()
    nodes.append(self._presetNode)
    for node in nodes:
      slicer.mrmlScene.RemoveNode(node)

  def setPresetNode(self, node: slicer.vtkMRMLScriptedModuleNode):
    if node and not node.GetAttribute("Type") == "ElastixPreset":
      raise AttributeError(f"Provided node {node.GetID()} needs to be of type 'ElastixPreset'")

    self._presetNode = node

    if self._presetNode:
      shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
      if self._presetNode.GetHideFromEditors():
        self._presetNode.SetHideFromEditors(False)
        shNode.RequestOwnerPluginSearch(self._presetNode)
        shNode.SetItemAttribute(shNode.GetItemByDataNode(self._presetNode), "Type", "ElastixPreset")

  def moveNodeToPresetFolder(self, node):
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    nodeItemId = shNode.GetItemByDataNode(self._presetNode)
    shNode.SetItemParent(shNode.GetItemByDataNode(node), nodeItemId)

  def getPresetNode(self) -> slicer.vtkMRMLScriptedModuleNode:
    return self._presetNode

  def _updateName(self):
    self._presetNode.SetName(f"{self.getModality()} ({self.getContent()})")

  def setID(self, value):
    self._presetNode.SetAttribute("id", str(value))

  def getID(self):
    return self._presetNode.GetAttribute("id")

  def setModality(self, value):
    self._presetNode.SetAttribute("modality", str(value))
    self._updateName()

  def getModality(self):
    return self._presetNode.GetAttribute("modality")

  def setContent(self, value: str):
    self._presetNode.SetAttribute("content", str(value))
    self._updateName()

  def getContent(self) -> str:
    return self._presetNode.GetAttribute("content")

  def setDescription(self, value: str):
    self._presetNode.SetAttribute("description", str(value))

  def getDescription(self) -> str:
    return self._presetNode.GetAttribute("description")

  def setPublications(self, value: str):
    self._presetNode.SetAttribute("publications", str(value))

  def getPublications(self) -> str:
    return self._presetNode.GetAttribute("publications")

  def setParameterFiles(self, value: List[slicer.vtkMRMLTextNode]):
    if type(value) is str:
      raise ValueError("Parameter files parameter needs to be a list of either file paths or vtkMRMLTextNodes")
    # accepts a list of nodes or ids
    for val in value:
      self.addParameterFile(val)

  def getParameterFiles(self) -> List:
    referenceRole = "parameterFiles"
    return [self._presetNode.GetNthNodeReference(referenceRole, idx)
            for idx in range(self._presetNode.GetNumberOfNodeReferences(referenceRole))]

  def addParameterFile(self, value: Union[str, slicer.vtkMRMLTextNode]):
    # check if file path and load into text file if so
    from pathlib import Path
    if os.path.exists(value) or Path(value).exists():  # is likely a path
      node = slicer.util.loadNodeFromFile(str(value))
    elif type(value) is str and value.startswith("vtkMRML"): # is mrml id
      node = slicer.util.getNode(value)
    else:  # has to be a mrmlNode
      node = cloneMRMLNode(value)
    referenceRole = "parameterFiles"
    nNodes = self._presetNode.GetNumberOfNodeReferences(referenceRole) + 1
    self._presetNode.SetNthNodeReferenceID(referenceRole, nNodes, node.GetID())
    self.moveNodeToPresetFolder(node)

  #
  # def addParameterFile(self):
  #   pass

  #
  # @property
  # def modality(self):
  #   return self._modality
  #
  # @property
  # def content(self):
  #   return self._content
  #
  # @property
  # def description(self):
  #   return self._description
  #
  # @property
  # def publications(self):
  #   return self._publications
  #
  # @property
  # def role(self):
  #   return self._role
  #
  # @property
  # def parameterFiles(self):
  #   return self._parameterFiles
  #
  # def addParameterFile(self, parameterFile):
  #   # file path or vtkMRMLTextNode depending on (if scripted module available or not)
  #
  #   if self.scriptedNode:
  #     referenceRole = 'parameterFiles'
  #     nNodes = self.scriptedNode.GetNumberOfNodeReferences(referenceRole) + 1
  #     self.scriptedNode.SetNthNodeReferenceID(referenceRole, nNodes, parameterFile.GetID())
  #   else:
  #     self._parameterFiles.append(parameterFile)
  #
  # def toScene(self):
  #   # could create scripted node and move all the info there
  #   pass
  #
  # def __init__(self, id:str, modality:str, content:str, description:str, publications:str, role:DatabaseRole, parameterFiles: List[str], scriptedNode: slicer.vtkMRMLScriptedModuleNode=None):
  #   self.scriptedNode = scriptedNode
  #
  #   # TODO: what if scripted node already has data ???
  #
  #   self.id = id
  #   self.modality = modality
  #   self.content = content
  #   self.description = description
  #   self.publications = publications
  #   self.role = role
  #   self.parameterFiles = parameterFiles
  #


def getInScenePreset(presetNode: slicer.vtkMRMLScriptedModuleNode):
  if presetNode is None:
    return None

  try:
    preset = InScenePresets[presetNode]
  except KeyError:
    preset = InScenePreset(presetNode)

    InScenePresets[presetNode] = preset
  return preset


def createPreset(id:str, modality:str, content:str, description:str, publications:str, parameterFiles: List[str] = None, inScene: bool = False):
  preset = InScenePreset() if inScene else Preset()
  preset.setID(id)
  preset.setModality(modality)
  preset.setContent(content)
  preset.setDescription(description)
  preset.setPublications(publications)
  preset.setParameterFiles(parameterFiles)
  return preset


def copyPreset(preset: Preset) -> InScenePreset:
  """ takes any preset and generates a InScenePreset from it

  :param preset:
  :return: instance of InScenePreset
  """
  presetCopy = InScenePreset()
  import random
  import base64
  presetCopy.setID(f"{preset.getID()}-{base64.urlsafe_b64encode(random.randbytes(6)).decode()}")
  presetCopy.setModality(preset.getModality())
  presetCopy.setContent(preset.getContent())
  presetCopy.setDescription(preset.getDescription())
  presetCopy.setPublications(preset.getPublications())
  presetCopy.setParameterFiles(preset.getParameterFiles())

  return presetCopy


def isWritable(preset: PresetBase):
  return isinstance(preset, InScenePreset)


def cloneMRMLNode(node):
  shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
  itemIDToClone = shNode.GetItemByDataNode(node)
  clonedItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode, itemIDToClone)
  return shNode.GetItemDataNode(clonedItemID)
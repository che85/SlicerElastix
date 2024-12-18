import json
from pathlib import Path


import slicer
from typing import List, Union, Dict

# for caching instead of persistently creating new preset for each node in the scene
InScenePresets = {}


class Preset:

  def __init__(self):
    self._data = {}

  def getName(self):
    return f"{self.getModality()} ({self.getContent()})"

  def getID(self):
    return self._getDictAttribute("id")

  def setID(self, value: str):
    self._data["id"] = value

  def getModality(self):
    return self._getDictAttribute("modality")

  def setModality(self, value: str):
    self._data["modality"] = value

  def getContent(self) -> str:
    return self._getDictAttribute("content")

  def setContent(self, value: str):
    self._data["content"] = value

  def getDescription(self) -> str:
    return self._getDictAttribute("description")

  def setDescription(self, value: str):
    self._data["description"] = value

  def getPublications(self) -> str:
    return self._getDictAttribute("publications")

  def setPublications(self, value: str):
    self._data["publications"] = value

  def setParameters(self, values: List[Dict[str, str]]):
    # TODO: check for proper types?
    self._data["parameter_files"] = values

  def getParameters(self):
    return self._getDictAttribute("parameter_files", [])

  def getParameterSectionNames(self) -> List:
    return [pf["name"] for pf in self._data["parameter_files"]]

  def addParameterSection(self, name, content: Union[str]):
    parameters = self.getParameters()
    parameters.append(
      {
        "name": name,
        "content": content
      }
    )

  def hasParameterSection(self, name):
    parameters = self.getParameters()
    for param in parameters:
      if param["name"] == name:
        return True
    return False

  def removeParameterSection(self, idx):
    parameters = self.getParameters()
    parameters.pop(idx)

  def getParameterSectionIndex(self, name):
    parameters = self.getParameters()
    for secIdx, param in enumerate(parameters):
      if param["name"] == name:
        return secIdx
    return -1

  def getParameterSectionContent(self, name):
    parameters = self.getParameters()
    for param in parameters:
      if param["name"] == name:
        return param["content"]
    return ""

  def getParameterSectionByIdx(self, idx):
    parameters = self.getParameters()
    return parameters[idx]

  def getParameterSectionContentByIdx(self, idx):
    return self.getParameterSectionByIdx(idx)["content"]

  def _getDictAttribute(self, key, default=""):
    try:
      return self._data[key]
    except KeyError:
      self._data[key] = default
      return self._data[key]

  def toJSON(self):
    return json.dumps(self._data, indent=2)


class InScenePreset(Preset):

  @staticmethod
  def createTextNode():
    presetNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode")
    presetNode.SetAttribute("Type", "ElastixPreset")
    return presetNode

  def __init__(self, presetNode: slicer.vtkMRMLTextNode = None):
    super().__init__()

    """ Creates new scripted node if none was defined

    :param presetNode:
    """
    if not presetNode:
      presetNode = self.createTextNode()
    self.setPresetNode(presetNode)

  def delete(self):
    slicer.mrmlScene.RemoveNode(self._presetNode)

  def setPresetNode(self, node: slicer.vtkMRMLTextNode):
    if node and not node.GetAttribute("Type") == "ElastixPreset":
      raise AttributeError(f"Provided node {node.GetID()} needs to be of type 'ElastixPreset'")

    self._presetNode = node

    if self._presetNode:
      shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
      if self._presetNode.GetHideFromEditors():
        self._presetNode.SetHideFromEditors(False)
        shNode.RequestOwnerPluginSearch(self._presetNode)
        shNode.SetItemAttribute(shNode.GetItemByDataNode(self._presetNode), "Type", "ElastixPreset")

    self._readFromTextNode()

  def getPresetNode(self) -> slicer.vtkMRMLTextNode:
    return self._presetNode

  def _updateTextNode(self):
    self._presetNode.SetText(
      json.dumps(self._data, indent=2)
    )
    self._presetNode.SetName(self.getName())

  def _readFromTextNode(self):
    text = self._presetNode.GetText()
    self._data = json.loads(text) if text else {}

  def setID(self, value):
    super().setID(value)
    self._updateTextNode()

  def setModality(self, value):
    super().setModality(value)
    self._updateTextNode()

  def setContent(self, value: str):
    super().setContent(value)
    self._updateTextNode()

  def setDescription(self, value: str):
    super().setDescription(value)
    self._updateTextNode()

  def setPublications(self, value: str):
    super().setPublications(value)
    self._updateTextNode()

  def setParameters(self, values: List[Dict[str, str]]):
    super().setParameters(values)
    self._updateTextNode()

  def addParameterSection(self, name, content: Union[str]):
    super().addParameterSection(name, content)
    self._updateTextNode()

  def setParameterSectionContentByIdx(self, idx, content):
    section = self.getParameterSectionByIdx(idx)
    section["content"] = content
    self._updateTextNode()

  def removeParameterSection(self, idx):
    super().removeParameterSection(idx)
    self._updateTextNode()

  def moveParameterSection(self, fromIdx, toIdx):
    parameters = self.getParameters()
    parameters.insert(toIdx, parameters.pop(fromIdx))
    self._updateTextNode()

def getInScenePreset(presetNode: slicer.vtkMRMLTextNode):
  if presetNode is None:
    return None

  try:
    preset = InScenePresets[presetNode]
  except KeyError:
    preset = InScenePreset(presetNode)

    InScenePresets[presetNode] = preset
  return preset


def createPreset(id:str, modality:str, content:str, description:str, publications:str, parameterFiles: List[str] = None):
  preset = Preset()
  preset.setID(id)
  preset.setModality(modality)
  preset.setContent(content)
  preset.setDescription(description)
  preset.setPublications(publications)

  for f in parameterFiles:
    with open(f, 'r') as file:
      file_content = file.read()
      preset.addParameterSection(
        Path(f).name,
        file_content
      )

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

  import copy
  presetCopy.setParameters(copy.deepcopy(preset.getParameters()))

  return presetCopy


def isWritable(preset: Preset):
  return isinstance(preset, InScenePreset)

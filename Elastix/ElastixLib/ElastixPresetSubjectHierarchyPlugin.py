import vtk, qt, ctk, slicer
import logging
from AbstractScriptedSubjectHierarchyPlugin import *

class ElastixPresetSubjectHierarchyPlugin(AbstractScriptedSubjectHierarchyPlugin):
  """ Scripted subject hierarchy plugin for the Segment Statistics module.

      This is also an example for scripted plugins, so includes all possible methods.
      The methods that are not needed (i.e. the default implementation in
      qSlicerSubjectHierarchyAbstractPlugin is satisfactory) can simply be
      omitted in plugins created based on this one.
  """

  # Necessary static member to be able to set python source to scripted subject hierarchy plugin
  filePath = __file__

  def __init__(self, scriptedPlugin):
    scriptedPlugin.name = 'ElastixPresets'
    AbstractScriptedSubjectHierarchyPlugin.__init__(self, scriptedPlugin)

  def canAddNodeToSubjectHierarchy(self, node, parentItemID = None):
    if node is not None and node.IsA("vtkMRMLScriptedModuleNode"):
      if node.GetAttribute("Type") == "ElastixPreset":
        return 0.9
    return 0.0

  def canOwnSubjectHierarchyItem(self, itemID):
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    shNode = pluginHandlerSingleton.subjectHierarchyNode()
    associatedNode = shNode.GetItemDataNode(itemID)
    return self.canAddNodeToSubjectHierarchy(associatedNode)

  def roleForPlugin(self):
    return "ElastixPreset"

  def helpText(self):
    # return ("<p style=\" margin-top:4px; margin-bottom:1px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">"
      # "<span style=\" font-family:'sans-serif'; font-size:9pt; font-weight:600; color:#000000;\">"
      # "HeartValves module subject hierarchy help text"
      # "</span>"
      # "</p>"
      # "<p style=\" margin-top:0px; margin-bottom:11px; margin-left:26px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">"
      # "<span style=\" font-family:'sans-serif'; font-size:9pt; color:#000000;\">"
      # "This is how you can add help text to the subject hierarchy module help box via a python scripted plugin."
      # "</span>"
      # "</p>\n")
    return ""

  def icon(self, itemID):
    import os
    iconPath = None
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    shNode = pluginHandlerSingleton.subjectHierarchyNode()
    associatedNode = shNode.GetItemDataNode(itemID)
    if associatedNode is not None and associatedNode.IsA("vtkMRMLScriptedModuleNode"):
      if associatedNode.GetAttribute("Type") == "ElastixPreset":
        iconPath = os.path.join(os.path.dirname(__file__), '../Resources/Icons/Elastix.png')
    if iconPath and os.path.exists(iconPath):
      return qt.QIcon(iconPath)
    # Item unknown by plugin
    return qt.QIcon()

  def visibilityIcon(self, visible):
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    return pluginHandlerSingleton.pluginByName('Default').visibilityIcon(visible)

  def editProperties(self, itemID):
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    pluginHandlerSingleton.pluginByName('Default').editProperties(itemID)

  def itemContextMenuActions(self):
    return []

  def sceneContextMenuActions(self):
    return []

  def showContextMenuActionsForItem(self, itemID):
    # Scene
    if itemID == slicer.vtkMRMLSubjectHierarchyNode.GetInvalidItemID():
      # No scene context menu actions in this plugin
      return

    # Volume but not LabelMap
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    if pluginHandlerSingleton.pluginByName('ElastixPresets').canOwnSubjectHierarchyItem(itemID):
      # Get current item
      currentItemID = pluginHandlerSingleton.currentItem()
      if currentItemID == slicer.vtkMRMLSubjectHierarchyNode.GetInvalidItemID():
        logging.error("Invalid current item")
        return
      self.HeartValvesAction.visible = True

  def tooltip(self, itemID):
    return "Elastix preset"

  def setDisplayVisibility(self, itemID, visible):
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    pluginHandlerSingleton.pluginByName('Default').setDisplayVisibility(itemID, visible)

  def getDisplayVisibility(self, itemID):
    pluginHandlerSingleton = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    return pluginHandlerSingleton.pluginByName('Default').getDisplayVisibility(itemID)

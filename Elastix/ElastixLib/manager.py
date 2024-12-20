import logging
import os
import qt
import slicer
from typing import Callable
from ElastixLib.database import BuiltinElastixDatabase, UserElastixDataBase, InSceneElastixDatabase
from ElastixLib.preset import *


def makeAction(parent, text, slot, icon=None):
  action = qt.QAction(text, parent)
  action.connect('triggered(bool)', slot)

  if icon is not None:
    action.setIcon(slicer.app.style().standardIcon(icon))

  parent.addAction(action)
  return action


class BlockSignals:
  def __init__(self, elements):
    self.elements = elements

  def __enter__(self):
    for elem in self.elements:
      elem.blockSignals(True)
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    for elem in self.elements:
      elem.blockSignals(False)


class PresetManagerLogic:

  @property
  def logCallback(self):
    return self._logCallback

  @logCallback.setter
  def logCallback(self, cb: Callable = None):
    self._logCallback = cb
    for db in self._databases:
      db.logCallback = cb

  def __init__(self):
    self._logCallback = None

    self.registrationPresets = None

    self.builtinDatabase = BuiltinElastixDatabase()
    self.inSceneDatabase = InSceneElastixDatabase()
    self.userDatabase = UserElastixDataBase()

    self._databases = [self.builtinDatabase, self.userDatabase, self.inSceneDatabase]

  def getBuiltinPresetsDir(self):
    return self.builtinDatabase.getPresetsDir()

  def getUserPresetsDir(self):
    return self.userDatabase.getPresetsDir()

  def getRegistrationPresets(self, force_refresh=False):
    if self.registrationPresets and not force_refresh:
      return self.registrationPresets

    self.registrationPresets = []
    for database in self._databases:
      self.registrationPresets.extend(database.getRegistrationPresets(force_refresh))

    return self.registrationPresets

  def getPresetByID(self, presetId) -> Preset:
    for preset in self.getRegistrationPresets():
      if preset.getID() == presetId:
        print(preset)
        return preset
    return None

  def getIdxByPresetId(self, presetId):
    for presetIndex, preset in enumerate(self.getRegistrationPresets()):
      if preset.getID() == presetId:
        return presetIndex
    message = f"Registration preset with id '{presetId}' could not be found.  Falling back to default preset."
    logging.warning(message)
    return 0

  def importUserDatabase(self, f: str):
    # TODO: implement reading from a folder or zip file and search for xml files
    # TODO: database from unzipped file and then copy presets into scene
    pass

  def exportUserDatabase(self):
    # TODO: implement
    # zip whole database and download
    pass

  def savePreset(self, preset: InScenePreset) -> str:
    if not isWritable(preset):
      raise TypeError(f"Only presets of type {InScenePreset.__class__.__name__} can be persisted to the UserDatabase")

    files = preset.getParameterFiles()
    tempPreset = copyPreset(preset)
    if len(files) > 0:
      try:
        import xml.etree.ElementTree as ET
        builtinXml = self.builtinDatabase.DATABASE_FILE
        elastixUserFolder = self.getUserPresetsDir()

        presetID = tempPreset.getID()
        outputFolder = Path(elastixUserFolder) / presetID
        outputFolder.mkdir(exist_ok=False)

        from shutil import copyfile
        presetXml = str(outputFolder / "preset.xml")
        copyfile(builtinXml, presetXml)

        # read builtin xml, remove all elements and add preset
        xml = ET.parse(presetXml)
        root = xml.getroot()
        root.clear()
        attributes = tempPreset.getMetaInformation(
          [ID_KEY, MODALITY_KEY, CONTENT_KEY, PUBLICATIONS_KEY, DESCRIPTION_KEY]
        )
        presetElement = ET.SubElement(root, "ParameterSet", attributes)
        parFilesElement = ET.SubElement(presetElement, "ParameterFiles")

        # Copy parameter files to database directory
        for file in files:
          filename = os.path.basename(file)
          newFilePath = os.path.join(outputFolder, filename)

          from shutil import move
          move(file, newFilePath)
          ET.SubElement(parFilesElement, "File", {"Name": filename})

        xml.write(presetXml)

        return presetID
      finally:
        tempPreset.delete()


class PresetManagerDialog:

  @property
  def selectionModel(self):
    return self.ui.listWidget.selectionModel()

  def __init__(self, manager: PresetManagerLogic):
    self.manager = manager
    self._currentPreset = None
    self.setup()

  def setup(self):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath("Elastix"))
    self.widget = slicer.util.loadUI(os.path.join(scriptedModulesPath, 'Resources', "UI/PresetManager.ui"))
    self.ui = slicer.util.childWidgetVariables(self.widget)

    self.ui.clonePresetButton.setIcon(qt.QIcon(":Icons/Small/SlicerEditCopy.png"))
    self.ui.savePresetButton.setIcon(qt.QIcon(":Icons/Small/SlicerSave.png"))

    self.ui.addButton.setIcon(qt.QIcon(":Icons/Add.png"))
    self.ui.removeButton.setIcon(qt.QIcon(":Icons/Remove.png"))

    # configure buttons
    self.ui.clonePresetButton.clicked.connect(self.onClonePresetButton)
    self.ui.savePresetButton.clicked.connect(self.onSavePresetButton)

    self.ui.addButton.clicked.connect(self.onAddButton)
    self.ui.removeButton.clicked.connect(self.onRemoveButton)

    self.ui.moveUpButton.clicked.connect(self.onMoveUpButton)
    self.ui.moveDownButton.clicked.connect(self.onMoveDownButton)

    self.ui.idBox.textChanged.connect(self.onIdChanged)
    self.ui.modalityBox.textChanged.connect(self.onModalityChanged)
    self.ui.contentBox.textChanged.connect(self.onContentChanged)
    self.ui.descriptionBox.textChanged.connect(self.onDescriptionChanged)
    self.ui.publicationsBox.textChanged.connect(self.onPublicationsChanged)

    self.selectionModel.selectionChanged.connect(self.updateGUI)

    self.ui.presetSelector.currentIndexChanged.connect(self.onPresetSelected)

    self.ui.textWidget.editingChanged.connect(self.onEditingChanged)
    self.ui.textWidget.setMRMLScene(slicer.mrmlScene)

    # self._openFileAction = makeAction(self.ui.toolButton, text="Open Parameter File", slot=self.onOpenFileAction,
    #                                   icon=qt.QStyle.SP_FileLinkIcon)
    # self._openFileLocationAction = makeAction(self.ui.toolButton, text="Open Parameter File Location",
    #                                           slot=lambda: self.onOpenFileAction(location=True),
    #                                           icon=qt.QStyle.SP_DirLinkIcon)

  def onIdChanged(self, text):
    self._currentPreset.setID(text)
    self.updateGUI()

  def onModalityChanged(self, text):
    self._currentPreset.setModality(text)
    self.updateGUI()
    self.refreshCurrentPresetName()

  def onContentChanged(self, text):
    self._currentPreset.setContent(text)
    self.updateGUI()
    self.refreshCurrentPresetName()

  def onDescriptionChanged(self, text):
    self._currentPreset.setDescription(text)
    self.updateGUI()

  def onPublicationsChanged(self, text):
    self._currentPreset.setPublications(text)
    self.updateGUI()

  def onEditingChanged(self, active):
    textNode = self.ui.textWidget.mrmlTextNode()
    if active is True and textNode is not None:
      import vtk
      self._textNodeObserver = textNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onTextChanged)

    if not active and self._textNodeObserver is not None:
      self._textNodeObserver = textNode.RemoveObserver(self._textNodeObserver)

  def onTextChanged(self, unused1=None, unused2=None):
    rowIndex = self.getSelectedRow()
    row = rowIndex.row()
    preset = self._currentPreset
    textNode = self.ui.textWidget.mrmlTextNode()
    preset.setParameterSectionContentByIdx(row, textNode.GetText())

  def refreshRegistrationPresetList(self):
    wasBlocked = self.ui.presetSelector.blockSignals(True)
    self.ui.presetSelector.clear()
    for preset in self.manager.getRegistrationPresets(force_refresh=True):
      self.ui.presetSelector.addItem(preset.getName())
    self.ui.presetSelector.blockSignals(wasBlocked)
    self.updateGUI()

  def refreshCurrentPresetName(self):
    self.ui.presetSelector.setItemText(self.ui.presetSelector.currentIndex, self._currentPreset.getName())

  def displayTextForIndex(self):
    rowIndex = self.getSelectedRow()
    textWidget = self.ui.textWidget
    textNode = textWidget.mrmlTextNode()
    if not rowIndex:
      textNode.SetText("")
      return
    preset = self._currentPreset
    row = rowIndex.row()
    sectionContent = preset.getParameterSectionContentByIdx(row)
    textNode.SetText(sectionContent)
    textWidget.readOnly = not isWritable(self._currentPreset)

  # def onOpenFileAction(self, location=False):
  #   selectedRow = self.getSelectedRow()
  #   if selectedRow:
  #     item = self.model.item(selectedRow.row(), 0)
  #     from pathlib import Path
  #     filepath = Path(item.text()).parent if location is True else item.text()
  #     import subprocess, os, platform
  #     if platform.system() == 'Darwin':  # macOS
  #       subprocess.call(('open', filepath))
  #     elif platform.system() == 'Windows':  # Windows
  #       os.startfile(filepath)
  #     else:  # linux variants
  #       subprocess.call(('xdg-open', filepath))

  def onClonePresetButton(self):
    if self._currentPreset is not None:
      from ElastixLib.preset import copyPreset
      # TODO: show dialog with proposed name (autofill with original preset's name).
      preset = self._currentPreset
      copyPreset(preset)
      self.refreshRegistrationPresetList()
      self.selectLastPreset()

  def onSavePresetButton(self):
    # Can only be done if InScenePreset is selected
    if isWritable(self._currentPreset):
      newPresetId = self.manager.savePreset(self._currentPreset)
      if newPresetId:
        self.refreshRegistrationPresetList()
        idx = self.manager.getIdxByPresetId(newPresetId)
        self.ui.presetSelector.currentIndex = idx

  def onAddButton(self):
    w = self.ui.listWidget
    text = qt.QInputDialog.getText(None, "Add registration section/step", "Name:")
    while self._currentPreset.hasParameterSection(text):
      text = qt.QInputDialog.getText(None, "Add registration section/step", "Name (unique name): ")
    if text:
      w.addItem(text)
      self._currentPreset.addParameterSection(text, "")
      self.onPresetSelected()

  def getSelectedPreset(self):
    return self._currentPreset

  def getSelectedRow(self):
    selectedRows = self.selectionModel.selectedRows()
    if selectedRows:
      return selectedRows[0]
    return None

  def onRemoveButton(self):
    selectedRow = self.ui.listWidget.currentRow
    if selectedRow != -1:
      self.ui.listWidget.takeItem(selectedRow)
      self._currentPreset.removeParameterSection(selectedRow)
      self.onPresetSelected()

  def onMoveUpButton(self):
    w = self.ui.listWidget
    currentRow = w.currentRow
    if currentRow > 0:
      self._moveItem(currentRow, currentRow - 1)
      w.setCurrentRow(currentRow - 1)
    self._currentPreset.moveParameterSection(currentRow, currentRow - 1)

  def onMoveDownButton(self):
    w = self.ui.listWidget
    currentRow = w.currentRow
    if currentRow < w.count + 1:
      self._moveItem(currentRow, currentRow + 1)
      w.setCurrentRow(currentRow + 1)
    self._currentPreset.moveParameterSection(currentRow, currentRow + 1)

  def _moveItem(self, fromRow, toRow):
    w = self.ui.listWidget
    currentItem = w.takeItem(fromRow)
    w.insertItem(toRow, currentItem)

  def updateGUI(self):
    w = self.ui.listWidget
    validParameterFiles = w.count > 0 and all(w.item(rowIdx) is not None for rowIdx in range(w.count))
    validFormData = validParameterFiles and self.ui.modalityBox.text != '' \
                    and self.ui.contentBox.text != '' and self.ui.descriptionBox.plainText != ''
    idExists = self.ui.idBox.text in [preset.getID() for preset in self.manager.getRegistrationPresets()]
    validId = self.ui.idBox.text != '' and not idExists
    # self.ui.idBoxWarning.text = "*" if idExists else ''
    #self.ui.idBoxWarning.toolTip = "*ParameterSet with given id already exists" if isWritable(preset)idExists else ''
    preset = self.manager.getRegistrationPresets()[self.ui.presetSelector.currentIndex]
    self.displayTextForIndex()

    self.enableToolButtons(preset)

  def selectLastPreset(self):
    self.ui.presetSelector.currentIndex = self.ui.presetSelector.count - 1

  def onPresetSelected(self):
    self._currentPreset = self.manager.getRegistrationPresets()[self.ui.presetSelector.currentIndex]
    self.autoPopulateForm()
    self.updateGUI()

  def autoPopulateForm(self):
    preset = self._currentPreset
    self._populateForm(preset)
    self._enableForm(preset)

    w = self.ui.listWidget
    w.clear()
    if preset:
      self.ui.listWidget.addItems(preset.getParameterSectionNames())

  def _populateForm(self, preset):
    with BlockSignals([self.ui.idBox, self.ui.modalityBox, self.ui.contentBox, self.ui.descriptionBox,
                       self.ui.publicationsBox]):
      self.ui.idBox.text = "" if not preset else preset.getID()
      self.ui.modalityBox.text = "" if not preset else preset.getModality()
      self.ui.contentBox.text = "" if not preset else preset.getContent()
      self.ui.descriptionBox.plainText = "" if not preset else preset.getDescription()
      self.ui.publicationsBox.plainText = "" if not preset else preset.getPublications()
    self.ui.typeLabel.text = ""

  def enableToolButtons(self, preset):
    selectedRow = self.getSelectedRow()
    presetWritable = preset is not None and isWritable(preset)
    self.ui.addButton.setEnabled(preset is not None and presetWritable)
    self.ui.toolButton.setEnabled(False)
    self.ui.removeButton.setEnabled(selectedRow is not None and preset is not None and presetWritable)
    self.ui.moveUpButton.setEnabled(selectedRow and selectedRow.row() > 0 and presetWritable)
    self.ui.moveDownButton.setEnabled(selectedRow and selectedRow.row() < self.ui.listWidget.count - 1 and presetWritable)

  def _enableForm(self, preset):
    enabled = isWritable(preset)
    for c in [self.ui.savePresetButton, self.ui.idBox, self.ui.modalityBox, self.ui.contentBox, self.ui.descriptionBox,
              self.ui.publicationsBox]:
      c.enabled = enabled

  def exec_(self, presetId):
    textNode = None
    try:
      textNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode")
      self.ui.textWidget.setMRMLTextNode(textNode)
      self.refreshRegistrationPresetList()
      self.ui.presetSelector.currentIndex = self.manager.getIdxByPresetId(presetId)
      self.onPresetSelected()
      returnCode = self.widget.exec_()
      return returnCode
    finally:
      if self.ui.textWidget.editing:
        self.ui.textWidget.cancelEdits()
      slicer.mrmlScene.RemoveNode(textNode)

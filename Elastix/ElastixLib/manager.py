import os
import qt
import slicer
from ElastixLib.database import BuiltinElastixDatabase, UserElastixDataBase, InSceneElastixDatabase
from ElastixLib.preset import Preset, InScenePreset, isWritable


class PathLineEditDelegate(qt.QItemDelegate):
  def __init__(self, parent):
    qt.QItemDelegate.__init__(self, parent)

  def createEditor(self, parent, option, index):
    import ctk
    pathLineEdit = ctk.ctkPathLineEdit(parent)
    pathLineEdit.filters = ctk.ctkPathLineEdit.Files
    pathLineEdit.nameFilters = ["*.txt"]
    return pathLineEdit

  def setEditorData(self, editor, index):
    editor.blockSignals(True)
    editor.currentPath = index.model().data(index) if index.model().data(index) else ''
    editor.blockSignals(False)

  def setModelData(self, editor, model, index):
    model.setData(index, editor.currentPath)


def makeAction(parent, text, slot, icon=None):
  action = qt.QAction(text, parent)
  action.connect('triggered(bool)', slot)

  if icon is not None:
    action.setIcon(slicer.app.style().standardIcon(icon))

  parent.addAction(action)
  return action


class PresetManagerLogic:

  def __init__(self):
    self.registrationPresets = None

    self.builtinDatabase = BuiltinElastixDatabase()
    self.inSceneDatabase = InSceneElastixDatabase()
    self.userDatabase = UserElastixDataBase()

    # TODO think about in scene?
    # clone into scene
    # create into scene
    # option to persist into user database, but then get rid of scene database

  def getBuiltinPresetsDir(self):
    return self.builtinDatabase.getPresetsDir()

  def getUserPresetsDir(self):
    return self.userDatabase.getPresetsDir()

  def getRegistrationPresets(self, force_refresh=False):
    if self.registrationPresets and not force_refresh:
      return self.registrationPresets

    self.registrationPresets = []
    for database in [self.builtinDatabase, self.inSceneDatabase, self.userDatabase]:
      self.registrationPresets.extend(database.getRegistrationPresets(force_refresh))

    return self.registrationPresets

  def getPresetByID(self, presetId) -> Preset:
    for preset in self.getRegistrationPresets():
      if preset.getID() == presetId:
        return preset
    return None

  def savePreset(self, preset: InScenePreset, keep=False):
    # after saving preset, should the preset be removed from the scene or keep it
    pass

  def getPresetByID(self, presetID: str):
    # find Preset
    pass

  def importPresets(self, directory):
    # TODO: implement reading from a folder or zip file and search for xml files
    pass

  def exportPreset(self, preset: InScenePreset):
    # persisting in scene preset to user/custom database
    # TODO: handle situation where id already in use
    # write txt node to txt file (need to have unique name)
    pass

  def savePreset(self, preset: InScenePreset):
    # create folder in db
    # create xml
    # copy txt files

    # TODO: check if preset exists and raise error if so (maybe allowing overwriting?)

    filenames = dialog.getParameterFiles()
    if len(filenames) > 0:
      from shutil import copyfile
      import xml.etree.ElementTree as ET
      presetDatabase = self.logic.databaseFile
      xml = ET.parse(presetDatabase)
      root = xml.getroot()
      attributes = dialog.getMetaInformation()

      presetElement = ET.SubElement(root, "ParameterSet", attributes)
      parFilesElement = ET.SubElement(presetElement, "ParameterFiles")

      # Copy parameter files to database directory
      for file in filenames:
        filename = os.path.basename(file)
        newFilePath = os.path.join(folder, filename)
        createFileCopy = True
        discard = False
        if os.path.exists(newFilePath):
          import hashlib
          # check if identical
          if hashlib.md5(open(newFilePath, 'rb').read()).hexdigest() == hashlib.md5(open(file, 'rb').read()).hexdigest():
            createFileCopy = False
          else:  # not identical but same name
            if self.overwriteParFile(filename):
              createFileCopy = True
            else:
              discard = True
        if createFileCopy:
          copyfile(file, newFilePath)
        if not discard:
          ET.SubElement(parFilesElement, "File", {"Name": filename})

      xml.write(presetDatabase)


class PresetManagerDialog:

  @property
  def selectionModel(self):
    return self.ui.tableView.selectionModel()

  def __init__(self, manager: PresetManagerLogic):
    # TODO: multiple database paths
    # TODO in memory presets (inside scene)
      # xml text node should reference txt files to make sure they are kept in same structure
      # TODO: maybe even use subject hierarchy to recreate subfolder structure
      # TODO: copy from existing preset to custom preset (similar to copy segments widget)

    self.manager = manager
    self._currentPreset = None
    self.setup()

  def setup(self):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath("Elastix"))
    self.widget = slicer.util.loadUI(os.path.join(scriptedModulesPath, 'Resources', "UI/PresetManager.ui"))
    self.ui = slicer.util.childWidgetVariables(self.widget)

    self.ui.clonePresetButton.setIcon(qt.QIcon(":Icons/Small/SlicerEditCopy.png"))

    self.model = qt.QStandardItemModel(1, 1)
    self.ui.tableView.setModel(self.model)
    self.ui.tableView.setItemDelegateForColumn(0, PathLineEditDelegate(self.model))
    self.model.removeRows(0, self.model.rowCount())

    # configure buttons
    self.ui.addButton.clicked.connect(self.onAddButton)
    self.ui.removeButton.clicked.connect(self.onRemoveButton)

    self.ui.moveUpButton.clicked.connect(self.onMoveUpButton)
    self.ui.moveDownButton.clicked.connect(self.onMoveDownButton)
    self.ui.buttonBox.clicked.connect(self.onResetButton)

    self.model.connect('rowsInserted(QModelIndex,int,int)', self.updateGUI)
    self.model.connect('rowsRemoved(QModelIndex,int,int)', self.updateGUI)
    self.model.connect('dataChanged(QModelIndex,QModelIndex)', self.updateGUI)

    self.ui.idBox.textChanged.connect(self.updateGUI)
    self.ui.modalityBox.textChanged.connect(self.updateGUI)
    self.ui.contentBox.textChanged.connect(self.updateGUI)
    self.ui.descriptionBox.textChanged.connect(self.updateGUI)

    self.selectionModel.selectionChanged.connect(self.updateGUI)

    self.ui.presetSelector.connect("activated(int)", self.onPresetSelected)

    self._openFileAction = makeAction(self.ui.toolButton, text="Open Parameter File", slot=self.onOpenFileAction,
                                      icon=qt.QStyle.SP_FileLinkIcon)
    self._openFileLocationAction = makeAction(self.ui.toolButton, text="Open Parameter File Location",
                                              slot=lambda: self.onOpenFileAction(location=True),
                                              icon=qt.QStyle.SP_DirLinkIcon)

    self.refreshRegistrationPresetList()

    self.ui.textWidget.setMRMLScene(slicer.mrmlScene)

    # TODO: add connecting to handle if displayed files modified
    # first clone it, then make it editable!

  def refreshRegistrationPresetList(self):
    wasBlocked = self.ui.presetSelector.blockSignals(True)
    self.ui.presetSelector.clear()
    self.ui.presetSelector.addItem('')
    for preset in self.manager.getRegistrationPresets():
      self.ui.presetSelector.addItem(f"{preset.getModality()} ({preset.getContent()})")
    self.ui.presetSelector.blockSignals(wasBlocked)
    self.onPresetSelected()
    self.updateGUI()

  def fileForSelectionExists(self, modelIndex):
    item = self.model.item(modelIndex.row(), 0)
    if item:
      return os.path.exists(item.text())

  def displayTextForIndex(self, rowIndex):
    textWidget = self.ui.textWidget
    crntTextNode = textWidget.mrmlTextNode()
    if crntTextNode:
      slicer.mrmlScene.RemoveNode(crntTextNode)
    textWidget.setMRMLTextNode(None)
    if not rowIndex:
      return
    item = self.model.item(rowIndex.row(), 0)
    if item and self.fileForSelectionExists(rowIndex):
      node = slicer.util.loadNodeFromFile(item.text())
      textWidget.setMRMLTextNode(node)
      textWidget.readOnly = not isWritable(self._currentPreset)

  def onOpenFileAction(self, location=False):
    selectedRow = self.getSelectedRow()
    if selectedRow:
      item = self.model.item(selectedRow.row(), 0)
      from pathlib import Path
      filepath = Path(item.text()).parent if location is True else item.text()
      import subprocess, os, platform
      if platform.system() == 'Darwin':  # macOS
        subprocess.call(('open', filepath))
      elif platform.system() == 'Windows':  # Windows
        os.startfile(filepath)
      else:  # linux variants
        subprocess.call(('xdg-open', filepath))

  def onAddButton(self):
    # TODO: need to make sure that when inScene, can add new node but that should be in scene and not a local file
    self.model.insertRow(self.model.rowCount())
    self.ui.tableView.setCurrentIndex(self.model.index(self.model.rowCount() - 1, 0))

  def getSelectedRow(self):
    selectedRows = self.selectionModel.selectedRows()
    if selectedRows:
      return selectedRows[0]
    return None

  def onRemoveButton(self):
    selectedRow = self.getSelectedRow()
    if selectedRow:
      self.model.removeRow(selectedRow.row())

  def onMoveUpButton(self):
    selectedRow = self.getSelectedRow()
    if not selectedRow or selectedRow.row() == 0:
      # already top most row
      return
    self._moveItem(selectedRow.row(), selectedRow.row() - 1)
    self.ui.tableView.setCurrentIndex(self.model.index(selectedRow.row() - 1, 0))

  def onMoveDownButton(self):
    selectedRow = self.getSelectedRow()
    if not selectedRow or selectedRow.row() == self.model.rowCount() - 1:
      # already bottom most row
      return
    self._moveItem(selectedRow.row(), selectedRow.row() + 1)
    self.ui.tableView.setCurrentIndex(self.model.index(selectedRow.row() + 1, 0))

  def onResetButton(self, button):
    if button is self.ui.buttonBox.button(qt.QDialogButtonBox.Reset):
      self.resetForm()

  def resetForm(self):
    self.widget.done(4)

  def _moveItem(self, fromRow, toRow):
    fromItem = self.model.takeItem(fromRow, 0)
    toItem = self.model.takeItem(toRow, 0)
    self.model.setItem(toRow, 0, fromItem)
    self.model.setItem(fromRow, 0, toItem)

  def getParameterFiles(self):
    parameterFiles = []
    for rowIdx in range(self.model.rowCount()):
      item = self.model.item(rowIdx, 0)
      if item:
        parameterFiles.append(item.text())
    return parameterFiles

  def getMetaInformation(self):
    attributes = {}
    attributes['content'] = self.ui.contentBox.text
    attributes['description'] = self.ui.descriptionBox.text
    attributes['id'] = self.ui.idBox.text
    attributes['modality'] = self.ui.modalityBox.text
    attributes['publications'] = self.ui.publicationsBox.plainText
    return attributes

  def updateGUI(self):
    valiParameterFiles = self.model.rowCount() > 0 and all(
      self.model.item(rowIdx, 0) is not None for rowIdx in range(self.model.rowCount()))
    validFormData = valiParameterFiles and self.ui.modalityBox.text != '' \
                    and self.ui.contentBox.text != '' and self.ui.descriptionBox.text != ''
    idExists = self.ui.idBox.text in [preset.getID() for preset in self.manager.getRegistrationPresets()]
    validId = self.ui.idBox.text != '' and not idExists
    # self.ui.idBoxWarning.text = "*" if idExists else ''
    self.ui.buttonBox.button(qt.QDialogButtonBox.Save).setEnabled(validId and validFormData)

    # TODO: display something about missing parameter files. Otherwise it will fail at some point...

    # self.ui.warningLabel.text = "*ParameterSet with given id already exists" if isWritable(preset)idExists else ''
    self.enableToolButtons()

  def onPresetSelected(self):
    self._currentPreset = None
    if self.getSelectedRow() != 0:
      self._currentPreset = self.manager.getRegistrationPresets()[self.ui.presetSelector.currentIndex - 1]
    self.autoPopulateForm()

  def autoPopulateForm(self):
    preset = self._currentPreset
    self._populateForm(preset)
    self._enableForm(preset)

    self.model.removeRows(0, self.model.rowCount())
    if preset:
      # TODO: need to handle in scene presets
      for pIdx, paramFile in enumerate(preset.getParameterFiles()):
        self.onAddButton()
        modelIndex = self.model.index(pIdx, 0)
        # TODO: think about the full path which doesn't apply to in scene preset
        # could encode using something like @scene/{mrmlId}
        self.model.setData(modelIndex, paramFile)

  def _populateForm(self, preset):
    self.ui.idBox.text = "" if not preset else preset.getID()
    self.ui.modalityBox.text = "" if not preset else preset.getModality()
    self.ui.contentBox.text = "" if not preset else preset.getContent()
    self.ui.descriptionBox.text = "" if not preset else preset.getDescription()
    self.ui.publicationsBox.plainText = "" if not preset else preset.getPublications()
    self.ui.typeLabel.text = ""

  def enableToolButtons(self):
    selectedRow = self.getSelectedRow()
    preset = None
    if self.ui.presetSelector.currentIndex != 0:
      preset = self.manager.getRegistrationPresets()[self.ui.presetSelector.currentIndex - 1]
    self.displayTextForIndex(selectedRow)
    presetWritable = preset is not None and isWritable(preset)
    self.ui.addButton.setEnabled(preset is not None and presetWritable)
    self.ui.toolButton.setEnabled(selectedRow is not None and self.fileForSelectionExists(selectedRow))
    self.ui.removeButton.setEnabled(selectedRow is not None and preset is not None and presetWritable)
    self.ui.moveUpButton.setEnabled(selectedRow and selectedRow.row() > 0 and presetWritable)
    self.ui.moveDownButton.setEnabled(selectedRow and selectedRow.row() < self.model.rowCount() - 1 and presetWritable)

  def _enableForm(self, preset):
    enabled = isWritable(preset)
    components = [self.ui.idBox, self.ui.modalityBox, self.ui.contentBox,self.ui.descriptionBox,self.ui.publicationsBox]
    for c in components:
      c.enabled = enabled

  def exec_(self):
    self.updateGUI()
    returnCode = self.widget.exec_()
    # TODO: cleanup temporary loaded text nodes
    return returnCode

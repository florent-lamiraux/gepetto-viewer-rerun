import logging
from enum import Enum
from math import tau
from typing import List, Union

import numpy as np
import rerun as rr

from .entity import Entity, MeshFromPath
from .scene import Scene

logger = logging.getLogger(__name__)


class Archetype(Enum):
    ARROWS3D = 0
    BOXES3D = 1
    CAPSULES3D = 2
    LINESTRIPS3D = 3
    MESH3D = 4
    MESH_FROM_PATH = 5
    POINTS3D = 6


class Client:
    def __init__(self):
        self.gui = Gui()

    def __repr__(self):
        return f"Client({self.gui})"


class Gui:
    def __init__(self):
        """
        sceneList : List of `Scene` class (name and associated recording)
        windowList : List of all window names
        entityList : List containing every Rerun archetypes,
                    each archetypes contain a list of `Entity` class.
                    Use `Enum Archetype` to get indices.
        """

        self.sceneList = []
        self.windowList = []
        self.entityList = [[] for _ in range(len(Archetype))]

    def __repr__(self):
        return (
            f"Gui(windowList={self.windowList}, "
            f"sceneList (size: {len(self.sceneList)}) = {self.sceneList}, "
            f"entityList (size: {len(self.entityList)}) = {self.entityList})"
        )

    def createWindow(self, name: str):
        assert isinstance(name, str), "Parameter 'name' must be a string"

        self.windowList.append(name)
        msg = (
            "createWindow() does not create any window, "
            "Rerun create both window and scene at the same time. "
            "Window will be created after calling addSceneToWindow()."
        )
        logger.info(msg)
        return name

    def createScene(self, sceneName: str):
        assert isinstance(sceneName, str), "Parameter 'sceneName' must be a string"

        self.sceneList.append(Scene(sceneName))
        msg = (
            "createScene() does not create any scene yet, "
            "Rerun create both window and scene at the same time. "
            "Window will be created after calling addSceneToWindow()."
        )
        logger.info(msg)

    def _getSceneIndex(self, sceneName: str):
        for index, scene in enumerate(self.sceneList):
            if scene.name == sceneName:
                return index
        return -1

    def addSceneToWindow(self, sceneName: str, wid: str):
        assert all(
            isinstance(name, str) for name in [sceneName, wid]
        ), "Parameters 'sceneName' and 'wid' must be strings"

        index = self._getSceneIndex(sceneName)
        if index == -1:
            logger.error(f"addSceneToWindow(): Unknown sceneName '{sceneName}'.")
            return False
        elif wid not in self.windowList:
            logger.error(f"addSceneToWindow(): Unknown windowName '{wid}'.")
            return False

        rec = rr.new_recording(application_id=wid, recording_id=sceneName, spawn=True)
        self.sceneList[index].setRec(rec)
        return True

    def _parseEntity(
        self, archetypeName: str, archetype: rr.archetypes, entityType: Archetype
    ):
        """
        Parse archetype name and log (or not) archetype :
            - if there is a scene specified in archetypeName :  <scene>/name
                it will log directly the archetype into the scene
            - if there is a '/' : <not a scene>/name
                it will need addToGroup() to be log in a scene
                every '/' will interpreted as a tree
            - if there is no '/', archetype will require addToGroup() to be logged
        """
        assert archetype is not None, "_parseEntity(): 'entity' must not be None"
        assert isinstance(
            entityType, Archetype
        ), "_parseEntity(): 'entityType' must be of type `enum Archetype`"

        charIndex = archetypeName.find("/")
        # If entityName contains '/' then search for the scene in self.sceneList
        if charIndex != -1 and charIndex != len(archetypeName) - 1:
            sceneName = archetypeName[:charIndex]
            sceneIndex = self._getSceneIndex(sceneName)

            if sceneIndex != -1:
                entityName = archetypeName[charIndex + 1 :]
                entity = Entity(entityName, archetype, self.sceneList[sceneIndex])
                self.entityList[entityType.value].append(entity)

                if entityType == Archetype.MESH_FROM_PATH:
                    # There is a bug with `log_file_from_path` and recordings.
                    # That's why we call `rec.to_native()`.
                    # 19/11/2024 - Issue : https://github.com/rerun-io/rerun/issues/8167
                    rr.log_file_from_path(
                        file_path=entity.archetype.path,
                        recording=self.sceneList[sceneIndex].rec.to_native(),
                    )
                else:
                    rr.log(
                        entityName,
                        entity.archetype,
                        recording=self.sceneList[sceneIndex].rec,
                    )
                msg = (
                    f"_parseEntity() creates a {entityType.name} for '{archetypeName}', "
                    f"and logs it directly to '{self.sceneList[sceneIndex].name}' scene."
                )
                logger.info(msg)
                return
        # Put entity to entityList, wait for addToGroup() to be logged
        entity = Entity(archetypeName, archetype)
        self.entityList[entityType.value].append(entity)
        msg = (
            f"_parseEntity() does not create a {entityType.name} for '{archetypeName}', "
            "it will be created when added to a group with addToGroup()."
        )
        logger.info(msg)

    def _getEntity(self, entityName: str):
        for entity_list in self.entityList:
            for entity in entity_list:
                if entity.name == entityName:
                    return entity
        return None

    def _isEntityInScene(self, entity: Entity, scene: Scene):
        if entity and entity.scenes:
            for s in entity.scenes:
                if scene == s:
                    return True
        return False

    def addFloor(self, floorName: str):
        assert isinstance(floorName, str), "Parameter 'floorName' must be a string"

        floor = rr.Boxes3D(
            sizes=[[200, 200, 0.5]],
            colors=[(125, 125, 125)],
            fill_mode="Solid",
        )
        self._parseEntity(floorName, floor, Archetype.BOXES3D)
        return True

    def addBox(
        self,
        boxName: str,
        boxSize1: List[Union[int, float]],
        boxSize2: List[Union[int, float]],
        boxSize3: List[Union[int, float]],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(boxName, str), "Parameter 'boxName' must be a string"
        assert all(
            isinstance(x, (int, float)) for x in [boxSize1, boxSize2, boxSize3]
        ), "Parameters 'boxSize' must be a numbers"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        box = rr.Boxes3D(
            sizes=[[boxSize1, boxSize2, boxSize3]],
            colors=[RGBAcolor],
            fill_mode="Solid",
            labels=[boxName],
        )
        self._parseEntity(boxName, box, Archetype.BOXES3D)
        return True

    def addArrow(
        self,
        name: str,
        radius: Union[int, float],
        length: Union[int, float],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(name, str), "Parameter 'name' must be a string"
        assert all(
            isinstance(x, (int, float)) for x in [radius, length]
        ), "Parameters 'radius' and 'length' must be a numbers"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        angle = np.arange(start=0, stop=tau, step=tau)
        arrow = rr.Arrows3D(
            radii=[[radius]],
            vectors=np.column_stack(
                [np.sin(angle) * length, np.zeros(1), np.cos(angle) * length]
            ),
            colors=[RGBAcolor],
            labels=[name],
        )
        self._parseEntity(name, arrow, Archetype.ARROWS3D)
        return True

    def resizeArrow(self, arrowName: str, radius: Union[int, float], length: Union[int, float]):
        assert isinstance(
            arrowName, str), "Parameter 'arrowName' must be a string"
        assert all(isinstance(x, (int, float)) for x in [radius, length]), \
            "Parameters 'radius' and 'length' must be a numbers"

        def createArrow(
            arrowName: str,
            radius: Union[int, float],
            length: Union[int, float],
            colors: List[Union[int, float]]
        ):
            angle = np.arange(start=0, stop=tau, step=tau)
            vectors = np.column_stack(
                [np.sin(angle) * length, np.zeros(1), np.cos(angle) * length])
            arrow = rr.Arrows3D(
                radii=[[radius]],
                vectors=vectors,
                colors=colors,
                labels=[arrowName],
            )
            return arrow

        charIndex = arrowName.find('/')
        # If arrowName contains '/' then search for the scene
        if charIndex != -1 and charIndex != len(arrowName) - 1:
            sceneName = arrowName[:charIndex]
            sceneIndex = self._getSceneIndex(sceneName)
            # Check if scene exists
            if sceneIndex != -1:
                entityName = arrowName[charIndex + 1:]
                entity = self._getEntity(entityName)
                scene = self.sceneList[sceneIndex]
                # if `entity` exists in `scene` then log it
                if entity and self._isEntityInScene(entity, scene):
                    newArrow = createArrow(
                        arrowName, radius, length, entity.archetype.colors.pa_array)
                    entity.archetype = newArrow
                    rr.log(entity.name, entity.archetype, recording=scene.rec)

                    msg = (
                        f"resizeArrow('{arrowName}'): Logging new arrow "
                        f"'{entityName}' in '{sceneName}' scene."
                    )
                    logger.info(msg)
                    return True
                else:
                    msg = (
                        f"resizeArrow({arrowName}): Arrow '{entityName}' "
                        f"does not exists in '{sceneName}' scene."
                    )
                    logger.error(msg)
                    return False

        entity = self._getEntity(arrowName)
        if not entity:
            logger.error(
                f"resizeArrow(): Arrow '{arrowName}' does not exists.")
            return False

        newArrow = createArrow(arrowName, radius, length,
                                entity.archetype.colors.pa_array)
        entity.archetype = newArrow
        if entity.scenes:
            for scene in entity.scenes:
                rr.log(entity.name, entity.archetype, recording=scene.rec)
                msg = (
                    f"resizeArrow(): Logging a new Arrow3D named '{entity.name}' "
                    f"in '{scene.name}' scene."
                )
                logger.info(msg)
        else:
            msg = (
                f"resizeArrow(): Resizing an Arrow3D named '{entity.name}'."
            )
            logger.info(msg)
        return True

    def addCapsule(
        self,
        name: str,
        radius: Union[int, float],
        height: Union[int, float],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(name, str), "Parameter 'name' must be a string"
        assert all(
            isinstance(x, (int, float)) for x in [radius, height]
        ), "Parameters 'radius' and 'height must be a numbers"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        capsule = rr.Capsules3D(lengths=[height], radii=[radius], colors=[RGBAcolor])
        self._parseEntity(name, capsule, Archetype.CAPSULES3D)
        return True

    def addLine(
        self,
        lineName: str,
        pos1: List[Union[int, float]],
        pos2: List[Union[int, float]],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(lineName, str), "Parameter 'lineName' must be a string"
        assert all(
            isinstance(x, (list, tuple)) for x in [pos1, pos2]
        ), "Parameters 'pos1' and 'pos2' must be a list or tuple of numbers"
        assert all(
            isinstance(nb, (int, float)) for x in [pos1, pos2] for nb in x
        ), "Parameters 'pos1' and 'pos2' must be a list or tuple of numbers"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        line = rr.LineStrips3D(
            [[pos1, pos2]],
            radii=[0.1],
            colors=[RGBAcolor],
            labels=[lineName],
        )
        self._parseEntity(lineName, line, Archetype.LINESTRIPS3D)
        return True

    def addSquareFace(
        self,
        faceName: str,
        pos1: List[Union[int, float]],
        pos2: List[Union[int, float]],
        pos3: List[Union[int, float]],
        pos4: List[Union[int, float]],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(faceName, str), "Parameter 'faceName' must be a string"
        assert all(
            isinstance(x, (list, tuple)) for x in [pos1, pos2, pos3, pos4]
        ), "Parameters 'pos' must be a list or tuple of numbers"
        assert all(
            isinstance(nb, (int, float)) for x in [pos1, pos2, pos3, pos4] for nb in x
        ), "Parameters 'pos' must be a list or tuple of numbers"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        mesh = rr.Mesh3D(
            vertex_positions=[pos1, pos2, pos3, pos4],
            triangle_indices=[[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]],
            vertex_colors=[RGBAcolor],
        )
        self._parseEntity(faceName, mesh, Archetype.MESH3D)
        return True

    def addTriangleFace(
        self,
        faceName: str,
        pos1: List[Union[int, float]],
        pos2: List[Union[int, float]],
        pos3: List[Union[int, float]],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(faceName, str), "Parameter 'faceName' must be a string"
        assert all(
            isinstance(x, (list, tuple)) for x in [pos1, pos2, pos3]
        ), "Parameters 'pos' must be a list or tuple of numbers"
        assert all(
            isinstance(nb, (int, float)) for x in [pos1, pos2, pos3] for nb in x
        ), "Parameters 'pos' must be a list or tuple of numbers"
        assert all(
            len(x) == 3 for x in [pos1, pos2, pos3]
        ), "Parameter 'pos' must be of length 3"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        mesh = rr.Mesh3D(
            vertex_positions=[pos1, pos2, pos3],
            vertex_colors=[RGBAcolor],
        )

        self._parseEntity(faceName, mesh, Archetype.MESH3D)
        return True

    def addSphere(
        self,
        sphereName: str,
        radius: Union[int, float],
        RGBAcolor: List[Union[int, float]],
    ):
        assert isinstance(sphereName, str), "Parameter 'sphereName' must be a string"
        assert isinstance(
            radius, (int, float)
        ), "Parameters 'radius' and 'length' must be a numbers"
        assert isinstance(
            RGBAcolor, (list, tuple)
        ), "Parameter 'RGBAcolor' must be a list or tuple"

        sphere = rr.Points3D(
            positions=[[0.0, 0.0, 0.0]],
            radii=[[radius]],
            colors=[RGBAcolor],
            labels=[sphereName],
        )
        self._parseEntity(sphereName, sphere, Archetype.POINTS3D)
        return True

    def _getRecording(self, recName: str):
        return next(
            (scene.rec for scene in self.sceneList if scene.name == recName), None
        )

    def _logArchetype(self, entityName: str, groupName: str):
        entity = self._getEntity(entityName)
        rec = self._getRecording(groupName)
        sceneIndex = self._getSceneIndex(groupName)

        if isinstance(entity.archetype, MeshFromPath):
            # There is a bug with `log_file_from_path` and recordings.
            # That's why we call `rec.to_native()`.
            # 19/11/2024 - Issue : https://github.com/rerun-io/rerun/issues/8167
            rr.log_file_from_path(
                file_path=entity.archetype.path, recording=rec.to_native()
            )
            logger.info(f"Logging Mesh from file named '{entity.name}'.")
            return True
        elif isinstance(entity.archetype, rr.archetypes.arrows3d.Arrows3D):
            logger.info(f"Logging Arrows3D named '{entity.name}'.")
        elif isinstance(entity.archetype, rr.archetypes.boxes3d.Boxes3D):
            logger.info(f"Logging Boxes3D named '{entity.name}'.")
        elif isinstance(entity.archetype, rr.archetypes.capsules3d.Capsules3D):
            logger.info(f"Logging Capsules3D named '{entity.name}'.")
        elif isinstance(entity.archetype, rr.archetypes.line_strips3d.LineStrips3D):
            logger.info(f"Logging LineStrip3D named '{entity.name}'.")
        elif isinstance(entity.archetype, rr.archetypes.mesh3d.Mesh3D):
            logger.info(f"Logging Mesh3D named '{entity.name}'.")
        elif isinstance(entity.archetype, rr.archetypes.points3d.Points3D):
            logger.info(f"Logging Points3D named '{entity.name}'.")
        else:
            return False
        entity.addScene(self.sceneList[sceneIndex])
        rr.log(
            entity.name,
            entity.archetype,
            recording=rec,
        )
        return True

    def addToGroup(self, nodeName: str, groupName: str):
        """
        Actual log of an entity
        """
        assert all(
            isinstance(name, str) for name in [nodeName, groupName]
        ), "Parameters 'nodeName' and 'groupName' must be strings"

        if self._getSceneIndex(groupName) == -1:
            logger.error(f"addToGroup(): Scene '{groupName}' does not exists.")
            return False
        if not self._getEntity(nodeName):
            logger.error(f"addToGroup(): Entity '{nodeName}' does not exists.")
            return False
        return self._logArchetype(nodeName, groupName)

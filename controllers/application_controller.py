"""
ApplicationController

Initialisation du SDK HORIBA
Découverte des périphériques
Gestion de la connexion
"""

from __future__ import annotations

from loguru import logger

from horiba_sdk.devices.device_manager import DeviceManager


class ApplicationController:

    def __init__(self):

        self.device_manager: DeviceManager | None = None

        self.monochromator = None

        self.camera = None

        self.connected = False

    async def initialize(self):

        logger.info("Initialisation du SDK HORIBA")

        self.device_manager = DeviceManager(
            start_icl=True,
            enable_binary_messages=True,
            enable_logging=True,
        )

        await self.device_manager.start()

        #
        # Monochromateur
        #

        if len(self.device_manager.monochromators) > 0:

            self.monochromator = self.device_manager.monochromators[0]

            logger.info("Monochromateur connecté")

        else:

            logger.warning("Aucun monochromateur détecté")

        #
        # CCD
        #

        if len(self.device_manager.charge_coupled_devices) > 0:

            self.camera = self.device_manager.charge_coupled_devices[0]

            logger.info("Caméra connectée")

        else:

            logger.warning("Aucune caméra détectée")

        self.connected = (
            self.monochromator is not None
            and self.camera is not None
        )

    async def shutdown(self):

        logger.info("Fermeture du SDK")

        if self.device_manager is not None:

            await self.device_manager.stop()

    def is_connected(self):

        return self.connected

    def get_monochromator(self):

        return self.monochromator

    def get_camera(self):

        return self.camera
# Changelog

## 0.2.1-dev1

- l’échec d’arrêt d’ICL ne masque plus l’erreur initiale de découverte ;
- message explicite pour `KeyError: 'devices'` pendant la découverte CCD ;
- Python matériel limité à `<3.14` dans le projet ;
- test de régression ajouté.

## 0.2.0-dev1

- backend matériel `EzSpecBackend` pour `horiba-sdk==1.0.3` ;
- démarrage et arrêt sécurisés de `DeviceManager` ;
- découverte du MicroHR et de la Syncerity ;
- diagnostic matériel ;
- initialisation asynchrone avec timeout ;
- déplacement en longueur d’onde ;
- sélection des réseaux 1 à 3 ;
- acquisition CCD avec ROI limitée au capteur ;
- extraction robuste des données CCD ;
- arrêt d’acquisition ;
- tests avec faux SDK ;
- 6 tests automatisés au total ;
- compatibilité NumPy 2.x conservée.

## 0.1.0-dev1

- socle logiciel, simulation, queue, événements, états et export.

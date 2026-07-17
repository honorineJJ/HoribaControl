# MicroHR Control — Python

Application complète pour piloter un monochromateur HORIBA MicroHR et une caméra Syncerity avec le SDK EzSpec.

Configuration cible :

- MicroHR : `0340-0913-MHRA`
- Connexion : USB, gérée par `ICL.exe`
- Caméra : Syncerity
- Windows 11
- SynerJY / LabSpec installé
- EzSpec SDK installé, activé et licencié

## Fonctions

- découverte et connexion au MicroHR et à la caméra ;
- initialisation mécanique optionnelle ;
- déplacement vers une longueur d’onde ;
- sélection du réseau 1, 2 ou 3 ;
- acquisition CCD ;
- scan spectral pas à pas ;
- arrêt d’urgence logiciel ;
- affichage des spectres ;
- export CSV, NPZ et JSON ;
- journalisation ;
- mode simulation sans matériel ;
- interface graphique et interface en ligne de commande.

## Installation Windows 11

Ouvrir PowerShell dans le dossier du projet :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

Le package officiel `horiba-sdk` nécessite que `ICL.exe` soit installé, activé et licencié.

## Démarrage graphique

```powershell
python run_gui.py
```

ou :

```powershell
microhr-control
```

## Tests sans matériel

Dans `config.yaml`, définir :

```yaml
application:
  simulation: true
```

Puis lancer l’application.

## Ligne de commande

```powershell
python run_cli.py status
python run_cli.py move 532
python run_cli.py acquire --output data\acquisition_532
python run_cli.py scan --start 500 --stop 600 --step 1 --output data\scan_500_600
python run_cli.py grating 1
python run_cli.py initialize
```

## Vérification matérielle importante

Les dimensions de ROI par défaut sont `1024 × 256`, avec binning vertical complet. Elles conviennent à de nombreuses configurations Syncerity, mais l’application vérifie la taille réelle du capteur et réduit automatiquement la ROI si nécessaire.

Les valeurs de gain et de vitesse dépendent de la caméra installée. Elles sont exposées dans la configuration retournée par le SDK et ne sont pas forcées par défaut.

## Structure

- `src/microhr_control/horiba_backend.py` : accès réel au SDK HORIBA ;
- `src/microhr_control/simulation_backend.py` : simulateur ;
- `src/microhr_control/controller.py` : logique de haut niveau ;
- `src/microhr_control/gui.py` : interface graphique ;
- `src/microhr_control/cli.py` : commandes terminal ;
- `src/microhr_control/data_io.py` : sauvegarde ;
- `config.yaml` : paramètres ;
- `tests/` : tests du mode simulation.

## Limite honnête

Le projet est complet au niveau logiciel et utilise les appels officiels du SDK. Il ne peut pas être validé physiquement ici contre votre MicroHR/Syncerity. La première exécution sur le banc permettra de confirmer la ROI exacte et les tokens propres à votre caméra.

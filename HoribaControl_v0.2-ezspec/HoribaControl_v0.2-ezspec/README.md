# HoribaControl v0.2-dev — EzSpec

Cette version ajoute le backend matériel officiel HORIBA EzSpec au socle v0.1.

## Matériel cible

- MicroHR `0340-0913-MHRA`
- caméra Syncerity
- connexion USB via `ICL.exe`
- Windows 11
- `horiba-sdk` 1.0.3

## Installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev,hardware]
pytest -q
```

## 1. Test sans matériel

```powershell
horibacontrol demo
```

## 2. Diagnostic matériel sans mouvement

Fermer LabSpec/SynerJY s’il utilise déjà le matériel, puis lancer :

```powershell
horibacontrol diagnose
```

Cette commande :

1. démarre ou rejoint ICL ;
2. découvre le MicroHR et la Syncerity ;
3. ouvre les deux périphériques ;
4. affiche leur configuration ;
5. les ferme proprement.

Copier la sortie complète et le fichier `logs/horibacontrol.log` en cas d’erreur.

## 3. Premier essai matériel complet

À exécuter seulement après réussite du diagnostic :

```powershell
horibacontrol hardware-smoke --wavelength 532 --grating 1
```

Résultats :

```text
data/hardware_smoke.csv
data/hardware_smoke.json
```

## Paramètres importants

Ils sont dans `config/default.yaml` :

- index du monochromateur et de la caméra ;
- adresse et port ICL ;
- délais d’attente ;
- temps d’exposition ;
- ROI et binning.

La ROI est automatiquement limitée à la taille réelle du capteur.

## Sécurité logicielle

Les mouvements et acquisitions sont séquentiels. Le programme interroge `is_busy()` ou `get_acquisition_busy()` jusqu’à la fin, avec timeout configurable.

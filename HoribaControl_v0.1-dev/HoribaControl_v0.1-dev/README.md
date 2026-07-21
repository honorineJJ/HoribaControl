# HoribaControl v0.1-dev

Socle logiciel testable pour le pilotage d’un HORIBA MicroHR et d’une caméra Syncerity.

## Matériel cible

- MicroHR : `0340-0913-MHRA`
- Connexion : USB via ICL / EzSpec
- Caméra : Syncerity
- Système : Windows 11

## Fonctionnalités de cette version

- configuration YAML ;
- journalisation ;
- bus d’événements ;
- file de commandes asynchrone ;
- machine d’états ;
- backend de simulation ;
- scénario complet : connexion → initialisation → déplacement → acquisition → sauvegarde → déconnexion ;
- export CSV et JSON ;
- tests automatisés ;
- compatibilité NumPy 2.x avec `numpy.trapezoid`.

Le backend matériel EzSpec sera ajouté à la version suivante sans modifier le cœur de l’application.

## Installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

## Démonstration

```powershell
horibacontrol demo
```

Le spectre est enregistré dans `data/demo_spectrum.csv`.

## Tests

```powershell
pytest -q
```

## Structure

```text
src/horibacontrol/
├── application.py
├── cli.py
├── config.py
├── core/
│   ├── command_queue.py
│   ├── event_bus.py
│   └── state_machine.py
├── domain/
│   ├── commands.py
│   ├── events.py
│   └── models.py
├── hardware/
│   ├── backend.py
│   └── simulation.py
└── services/
    └── spectrum_io.py
```

## Étape suivante

La v0.2 branchera le SDK officiel HORIBA EzSpec sur l’interface `InstrumentBackend`.

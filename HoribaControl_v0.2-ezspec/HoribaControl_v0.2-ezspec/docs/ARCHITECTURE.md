# Architecture v0.1

La GUI, le CLI ou un script envoient des commandes à `CommandQueue`.

`CommandQueue` garantit l’exécution séquentielle et pilote :

1. la machine d’états ;
2. le backend matériel ou simulé ;
3. le bus d’événements ;
4. les résultats ou exceptions.

Le reste de l’application ne dépend que de `InstrumentBackend`.
La v0.2 pourra donc ajouter `EzSpecBackend` sans réécrire la logique métier.

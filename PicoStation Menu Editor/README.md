# PicoStation Menu Editor

Éditeur web local, sans serveur externe ni dépendance JavaScript à installer.

Sur macOS, double-clique sur **Lancer.command**. Sinon, depuis la racine du dépôt :

```sh
python3 tools/serve_editor.py
```

Le serveur est accessible seulement sur ton ordinateur. Les PNG sont lus et convertis dans le navigateur. Il faut ouvrir l'application par ce lanceur, pas directement en `file://`, pour charger les modules et le convertisseur.

Fonctions : cinq couleurs (fond, cadre, liste, curseur, texte), styles Covers/Classic, boutons Ouvrir/Retour, import et réinitialisation de configuration, import PNG du fond 320×240 et du logo 128×20, aperçu, export `config.ini` ou ZIP contenant les fichiers à placer à la racine de la SD.

Les dimensions sont contrôlées ; les images ne sont pas étirées automatiquement. Le fond doit être opaque. Le logo conserve son alpha complet. Le fond est ramené à une palette de 256 couleurs au format PS1. Le sélecteur de langue est volontairement absent.

Les réglages sont mémorisés localement dans le navigateur. Les images restent en mémoire pendant la session. Lors de l'import d'un INI, les clés inconnues valides sont préservées, sauf `lang`. Si une image activée n'est pas importée dans l'éditeur, l'export contient seulement sa configuration et conserve le fichier déjà présent sur la SD.

Le ZIP contient directement les fichiers à la racine, sans dossier intermédiaire. Son extraction doit remplacer les anciens fichiers concernés. La case du logo génère `logo=0/1`, pour pouvoir désactiver un ancien `logo.raw` encore présent sur la SD.

Le fond fonctionne avec RC5 ; le logo externe nécessite RC5.CS01. L'aperçu reproduit les dimensions, placements, couleurs converties et composition du logo. La jaquette affichée est un exemple ; l'aperçu n'est pas une émulation complète du GPU PS1.

# RC5 PU18 / PU8 et extension CS02

Cette chaîne cible les cartes PS1 **PU18 et PU8, Pico RP2040, sans overclock**. Aucune variante overclockée ou Pico 2 n’est produite. Les essais utilisateur CS01 ont confirmé le démarrage, les jeux et la personnalisation sur PU18. CS02 corrige le défaut du coin inférieur droit ; les contrôles et l’essai visuel du diagnostic CS02 sur PU18 confirment la réception intégrale du fond et la disparition du rectangle. La PU8 reste à vérifier sur le matériel.

## Nature de la reconstruction

Les sources publiques de janvier 2026 ne permettent pas de reconstruire la RC5 publiée en juillet. Ce fork conserve leur historique, mais utilise pour la nouvelle chaîne une **base RC5 récupérée sans perte**, puis des **extensions écrites en C**.

Les fichiers `original/*.S` sont une représentation assembleur des données et du code machine récupérés. Ils contiennent des directives de données avec les positions d'origine. **Ils ne sont pas les sources C/C++ originales retrouvées, ni une réécriture intégrale de la RC5 en C/C++.** Les sources originales non publiées restent indisponibles.

L’assemblage et la sélection de carte reproduisent exactement chaque UF2 officiel de référence :

```text
SHA-256 31e0231d8abc243bec6c8a788d3d027f3af97354ae48edacb79aa1acb498b702
500736 octets — picostation_PU18.uf2, RC5 officielle

SHA-256 6df7b93ba5dbc82b4e350955607f3c1e644fdf386b12607a8bdb45120a099e9c
500736 octets — picostation_PU8.uf2, RC5 officielle
```

Les deux images officielles sans overclock ne diffèrent que par deux octets dans la flash : `0x3cb18` (`3f` → `43`) et `0x3cb22` (`20` → `22`). `original/manifest.json` conserve ces différences, les valeurs attendues et les empreintes de chaque carte. La base PU18 est assemblée, puis ces différences sont appliquées pour PU8 avant vérification de son empreinte officielle. Il n’est pas nécessaire de dupliquer l’image assembleur complète. Le disque du menu et les adresses de l’extension sont identiques sur les deux cartes.

Référence : [release RC5 officielle](https://github.com/megavolt85/PicoStation/releases/tag/RC5), archive `picostation_pico1_RC5.7z`, SHA-256 `71ae613d9c875313e6e9e2e970f81edc3942d712f396a150c3336a70c079b81a`.

Les fonctions RC5 de lecture des jeux, cartes mémoire, jaquettes, cheats, options, configuration et rendu sont conservées dans cette base. Leur présence et la conservation du code ne remplacent pas un essai de fonctionnement sur console.

## Compilation

Outils requis : Python 3.10+, GNU Arm Embedded (`arm-none-eabi-gcc`, `arm-none-eabi-as`, `arm-none-eabi-objcopy`), LLVM Clang avec cible MIPS I, LLD et LLVM (`llvm-objcopy`, `llvm-nm`). Sur le Mac de développement : GNU Arm 15.3, LLVM/LLD 23.1.4.

```sh
git submodule update --init third_party/ucl
python3 tools/rc5/build.py --board PU18
python3 tools/rc5/build.py --board PU8
```

Le script trouve les outils dans le PATH ou dans leurs installations Homebrew habituelles. Le compresseur UCL est construit pour l'ordinateur ; il n'est pas ajouté au firmware. Son sous-module est fixé au commit `d72326a913206ddf73d756feafff2d2dd42a733a`.

La carte choisie est PU18 si l’argument `--board` est absent. Les fichiers de chaque carte sont isolés dans `build-cs/PU18/` ou `build-cs/PU8/` :

- `picostation_<CARTE>_RC5-reconstruit.uf2` : référence reconstruite et vérifiée identique à la RC5 de cette carte.
- `picostation_<CARTE>_RC5.CS02-experimental.uf2` : extension CS02 de cette carte.
- `build-report.json` : empreintes, adresses des modifications, tailles et paramètres du build.

Les fichiers déjà produits par l’ancienne chaîne à la racine de `build-cs/` ne sont pas supprimés ; les nouveaux résultats sont dans les sous-dossiers par carte. Le code C de personnalisation et les fichiers SD sont communs aux deux cartes. Les deux variantes CS02 conservent les deux différences de carte vérifiées dans les firmwares officiels.

## Ce qui change

`patches/arm_logo.c` remplace le lecteur de parties du fond par un lecteur compatible avec les 34 parties RC5 et cinq parties supplémentaires pour `logo.raw`. Le changement est limité au menu. Le firmware de lecture des disques et ses réglages d'horloge ne sont pas remplacés.

CS02 rouvre le fichier correspondant à chaque bloc demandé. Le préchargement CD peut lire des blocs du logo avant que les dernières lectures du fond soient consommées, même avec `logo=0`. CS01 réutilisait le même fichier FatFs ouvert : les dernières lectures du fond pouvaient alors atteindre la fin de `logo.raw` et renvoyer zéro octet. Le chargeur RC5 acceptait ces réponses et conservait une zone vide. La sélection par bloc empêche cette confusion dans les deux sens ; la taille du fichier et le nombre d’octets lus sont également contrôlés.

`patches/ps1_logo.c` ajoute le chargement optionnel du logo après l'initialisation RC5, puis son dessin dans les deux styles. Le menu RC5 reste compacté en NRV2E et dans la même allocation CD. Le fichier compacté est chargé plus haut en RAM pour éviter qu'il soit écrasé pendant son propre décompactage.

Le lecteur vérifie la taille de `logo.raw` et les résultats de lecture. Une absence de fichier, une erreur ou des données de transport invalides conserve le logo embarqué. La clé `logo=0` désactive le logo externe ; `logo=1` l'active. Sans clé `logo`, le fichier est essayé s'il existe.

Le nouveau logo occupe une zone VRAM libre : x=768, y=0, 128×20, texture 16 bpp. Les ressources RC5 existantes restent à leurs positions. La transparence partielle est composée avec le fond au chargement ; les pixels entièrement transparents restent transparents. Les pixels noirs opaques restent opaques.

Le début du tas PS1 est déplacé après le code et le tampon ajoutés afin que les allocations de listes/cheats ne les écrasent pas. L'allocateur RC5 original est testé avec cette nouvelle limite. Le libellé de version du menu devient `RC5.CS02`.

## Formats à la racine de la SD

| Fichier | Format |
|---|---|
| `config.ini` | Texte, au plus 2048 octets ; valeurs hexadécimales |
| `background.raw` | 77312 octets : palette PS1 256×16 bits little endian, bloc gauche 256×240 indices, bloc droit 64×240 indices |
| `logo.raw` | 10240 octets : RGBA8888, pixels ligne par ligne, 128×20, alpha 0 transparent / 255 opaque |

Le fond est compatible avec la RC5 d'origine. `logo.raw` demande CS01 ou plus récent. Le logo n'est pas un TIM ni une texture RGB555 brute malgré son extension `.raw`.

Réglages par défaut :

```ini
background=000020
frame=FFFFFF
filelist=000040
cursor=800000
text=FFFFFF
style=0
wallpaper=0
actopen=E
actback=D
logo=0
```

`style=0` : Covers ; `style=1` : Classic. Boutons : `E` Croix, `D` Rond, `F` Carré, `C` Triangle. `wallpaper=1` active `background.raw`. Le firmware conserve les langues RC5 ; l'éditeur n'expose ni ne génère de réglage de langue.

## Vérifications

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
node tools/test_editor.mjs
.venv/bin/python tests/firmware.py --board PU18
.venv/bin/python tests/firmware.py --board PU8
```

Les essais exécutent le vrai code compilé ARM et MIPS. Les accès SD, le BIOS et les transferts GPU sont simulés aux interfaces. Ils vérifient le décompactage réel, le retour à l'entrée du menu RC5, le transport du fond, les cinq parties du logo, les tailles invalides, les erreurs de lecture, l'alpha, le noir opaque, les deux styles, l'alignement DMA et le repli sur le logo embarqué. Les EDC/ECC du disque embarqué sont contrôlés. Les octets modifiés sont bornés et comparés à la base.

GitHub Actions compile et exécute ces vérifications pour les deux cartes avec une matrice PU18/PU8 et publie un artefact par carte. Les rapports automatiques conservent `hardware_validated=false` : une simulation ne constitue pas une validation matérielle.

Ces tests **ne simulent pas toute la console ni le moteur de lecture des jeux**. Le retour utilisateur confirme le démarrage, le lancement des jeux et la personnalisation sur PU18, sans valider toutes les fonctions RC5. La PU8 demande encore un essai matériel. Aucun flashage automatique n’est effectué par les scripts.

Pour revenir à la version de référence, utilise l'UF2 RC5 original ou le fichier reconstruit dont l'empreinte est vérifiée ci-dessus. Conserve aussi les fichiers et réglages de ta SD.

## Diagnostic du fond sur console

Le mode optionnel ci-dessous photographie l’état du chargement au démarrage. Il demande `logo=0` pour observer le dernier paquet du fond. Les trois lignes en haut à droite, à la place du logo, affichent : `R`, CRC32 de la tuile droite en RAM ; `P`, CRC32 du dernier paquet ; `L`, longueur de sa charge utile ; `S`, taille du fichier vue par FatFs ; `F`, position de lecture dans ce fichier. Les nombres sont hexadécimaux.

```sh
python3 tools/rc5/build.py --board PU18 --diagnostic-background
.venv/bin/python tests/firmware.py --board PU18 --diagnostic-background
.venv/bin/python tests/background_diagnostic.py --board PU18
```

L’UF2 `picostation_PU18_RC5.CS02-background-diagnostic.uf2` et ses rapports sont dans `build-cs/PU18/background-diagnostic-CS02/`. Les informations FatFs passent dans le remplissage inutilisé du dernier paquet, sans changer ses octets d’image. Ce mode sert à vérifier le chargement du fond sur console. Il inclut le correctif CS02 et remplace temporairement le logo par les mesures. Les fichiers de la SD ne sont pas modifiés par le build.

# RC5 PU18 et extension CS01

Cette première version cible exclusivement **la carte PS1 PU18, Pico RP2040, sans overclock**. Aucune variante PU8, overclockée ou Pico 2 n'est produite par cette chaîne.

## Nature de la reconstruction

Les sources publiques de janvier 2026 ne permettent pas de reconstruire la RC5 publiée en juillet. Ce fork conserve leur historique, mais utilise pour la nouvelle chaîne une **base RC5 récupérée sans perte**, puis des **extensions écrites en C**.

Les fichiers `original/*.S` sont une représentation assembleur des données et du code machine récupérés. Ils contiennent des directives de données avec les positions d'origine. **Ils ne sont pas les sources C/C++ originales retrouvées, ni une réécriture intégrale de la RC5 en C/C++.** Les sources originales non publiées restent indisponibles.

L'assemblage de cette base reproduit exactement l'UF2 de référence :

```text
SHA-256 31e0231d8abc243bec6c8a788d3d027f3af97354ae48edacb79aa1acb498b702
500736 octets — picostation_PU18.uf2, RC5 officielle
```

Les fonctions RC5 de lecture des jeux, cartes mémoire, jaquettes, cheats, options, configuration et rendu sont conservées dans cette base. Leur présence et la conservation du code ne remplacent pas un essai de fonctionnement sur console.

## Compilation

Outils requis : Python 3.10+, GNU Arm Embedded (`arm-none-eabi-gcc`, `arm-none-eabi-as`, `arm-none-eabi-objcopy`), LLVM Clang avec cible MIPS I, LLD et LLVM (`llvm-objcopy`, `llvm-nm`). Sur le Mac de développement : GNU Arm 15.3, LLVM/LLD 23.1.4.

```sh
git submodule update --init third_party/ucl
python3 tools/rc5/build.py
```

Le script trouve les outils dans le PATH ou dans leurs installations Homebrew habituelles. Le compresseur UCL est construit pour l'ordinateur ; il n'est pas ajouté au firmware. Son sous-module est fixé au commit `d72326a913206ddf73d756feafff2d2dd42a733a`.

Résultats dans `build-cs/` :

- `picostation_PU18_RC5-reconstruit.uf2` : référence reconstruite et vérifiée identique à la RC5.
- `picostation_PU18_RC5.CS01-experimental.uf2` : extension CS01, **non validée sur console**.
- `build-report.json` : empreintes, adresses des modifications, tailles et paramètres du build.

## Ce qui change

`patches/arm_logo.c` remplace le lecteur de parties du fond par un lecteur compatible avec les 34 parties RC5 et cinq parties supplémentaires pour `logo.raw`. Le changement est limité au menu. Le firmware de lecture des disques et ses réglages d'horloge ne sont pas remplacés.

`patches/ps1_logo.c` ajoute le chargement optionnel du logo après l'initialisation RC5, puis son dessin dans les deux styles. Le menu RC5 reste compacté en NRV2E et dans la même allocation CD. Le fichier compacté est chargé plus haut en RAM pour éviter qu'il soit écrasé pendant son propre décompactage.

Le lecteur vérifie la taille de `logo.raw` et les résultats de lecture. Une absence de fichier, une erreur ou des données de transport invalides conserve le logo embarqué. La clé `logo=0` désactive le logo externe ; `logo=1` l'active. Sans clé `logo`, le fichier est essayé s'il existe.

Le nouveau logo occupe une zone VRAM libre : x=768, y=0, 128×20, texture 16 bpp. Les ressources RC5 existantes restent à leurs positions. La transparence partielle est composée avec le fond au chargement ; les pixels entièrement transparents restent transparents. Les pixels noirs opaques restent opaques.

Le début du tas PS1 est déplacé après le code et le tampon ajoutés afin que les allocations de listes/cheats ne les écrasent pas. L'allocateur RC5 original est testé avec cette nouvelle limite. Le libellé de version du menu devient `RC5.CS01`.

## Formats à la racine de la SD

| Fichier | Format |
|---|---|
| `config.ini` | Texte, au plus 2048 octets ; valeurs hexadécimales |
| `background.raw` | 77312 octets : palette PS1 256×16 bits little endian, bloc gauche 256×240 indices, bloc droit 64×240 indices |
| `logo.raw` | 10240 octets : RGBA8888, pixels ligne par ligne, 128×20, alpha 0 transparent / 255 opaque |

Le fond est compatible avec la RC5 d'origine. `logo.raw` demande CS01. Le logo n'est pas un TIM ni une texture RGB555 brute malgré son extension `.raw`.

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
.venv/bin/python tests/firmware.py
node tools/test_editor.mjs
```

Les essais exécutent le vrai code compilé ARM et MIPS. Les accès SD, le BIOS et les transferts GPU sont simulés aux interfaces. Ils vérifient le décompactage réel, le retour à l'entrée du menu RC5, le transport du fond, les cinq parties du logo, les tailles invalides, les erreurs de lecture, l'alpha, le noir opaque, les deux styles, l'alignement DMA et le repli sur le logo embarqué. Les EDC/ECC du disque embarqué sont contrôlés. Les octets modifiés sont bornés et comparés à la base.

Ces tests **ne simulent pas toute la console ni le moteur de lecture des jeux**. Le démarrage sur PS1, les changements de jeux, les cartes mémoire, le son, les cheats et les options demandent encore une validation matérielle de CS01. Aucun flashage automatique n'est effectué par les scripts.

Pour revenir à la version de référence, utilise l'UF2 RC5 original ou le fichier reconstruit dont l'empreinte est vérifiée ci-dessus. Conserve aussi les fichiers et réglages de ta SD.

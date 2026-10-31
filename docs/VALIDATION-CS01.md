# Validation locale RC5.CS01

Version cible : PU18, RP2040, sans overclock.

## Reconstruction

- UF2 RC5 reconstruit identique à la référence, SHA-256 : `31e0231d8abc243bec6c8a788d3d027f3af97354ae48edacb79aa1acb498b702`.
- UF2 CS01 expérimental local, SHA-256 : `6ee95ce3cb7bf22b1f27ac23a097a3065f19492b59248717ad247eea4a6e0cf9`.
- Extension ARM : 237 octets ; extension PS1, stockage inclus : 6536 octets.
- Tas PS1 déplacé à `0x8005d988` pour réserver cette extension.

## Essais automatisés

- baseline identical; modifications confined to declared ranges; CD EDC/ECC valid.
- actual packed entry reaches original RC5 entry and unpacks exact modified menu.
- original allocator preserves extension code/storage across directory-sized allocations.
- compiled MIPS I extension has no immediate load-use hazards.
- compiled ARM reader: original background, all RGBA parts, missing/invalid files, I/O failures, restart.
- compiled MIPS client + compiled ARM reader: both styles, flat/wallpaper backgrounds, exact alpha/black, DMA alignment, fallback/retry/disable.
- JavaScript editor ZIP decoded by compiled ARM/MIPS code: every pixel, both styles and tile boundary.
- config defaults, hexadecimal buttons, import validation, language omitted.
- background 77312 bytes, palette, left/right tile boundary and last row.
- deterministic quantization beyond 256 colors.
- logo RGBA including half alpha, transparent pixels, opaque black.
- PNG signature and exact dimensions.
- ZIP generation with three root files.

## Essais dans le navigateur

- Styles Covers et Classic, choix des touches et modification de la couleur vérifiés.
- Import PNG 320×240 opaque et 128×20 avec alpha vérifié.
- Image 100×100 rejetée avec ses dimensions affichées.
- ZIP téléchargé réellement ; présence des trois fichiers à sa racine, tailles, configuration et CRC contrôlés avec un lecteur ZIP indépendant.
- Aperçu sauvegardé dans `docs/editor-preview.png`.

## Limites restantes

**Aucun flashage ni essai sur console.** Les interfaces SD, BIOS et GPU sont simulées aux frontières dans les essais ARM/MIPS. Le moteur complet de la console et la compatibilité des jeux ne sont pas émulés par ces tests. Les fonctions RC5 restent dans la base, mais leur fonctionnement avec CS01 doit encore être confirmé sur PS1.

Les C/C++ originaux non publiés de RC5 ne sont pas récupérés. La base fidèle est une représentation assembleur de ses octets ; les extensions nouvelles sont en C.

Les empreintes CS01 dépendent du compilateur ; les versions sont enregistrées dans le rapport de build. L’empreinte de la RC5 reconstruite reste contrôlée par la chaîne.

# Office Asset Inventory

## Available Sprites (from pixelspaces_free)

### Usable for Office — HIGH PRIORITY

| Asset | Size | Category | Office Use |
|---|---|---|---|
| **Laptop.png** | 10x7 | Furniture/Bedroom | On desks |
| **Table_medium.png** | 14x7 | Furniture/Living Room | Desk surface |
| **Table_long.png** | 28x7 | Furniture/Living Room | Conference table |
| **Bookshelf_1.png** | 14x23 | Furniture/Living Room | Office bookshelf |
| **Bookshelf_small.png** | 14x12 | Furniture/Living Room | Small shelf unit |
| **Cabinet_1.png** | 14x23 | Furniture/Bedroom | Filing cabinet |
| **Drawer_medium_1_a.png** | 12x13 | Furniture/Bedroom | Desk drawer |
| **Drawer_medium_1_c.png** | 12x13 | Furniture/Bedroom | Desk drawer (alt) |
| **Lamp_stand_1.png** | 11x22 | Furniture/Bedroom | Floor lamp |
| **Lamp_stand_2.png** | 7x23 | Furniture/Bedroom | Tall lamp |
| **Lamp_bedroom_3.png** | 10x7 | Furniture/Bedroom | Ceiling/desk lamp |
| **Shelf_medium.png** | 14x5 | Furniture/Living Room | Wall shelf |
| **Shelf_large.png** | 28x5 | Furniture/Living Room | Long wall shelf |
| **Window_square.png** | 14x15 | Furniture/Living Room | Office window |
| **Window_circle.png** | 14x15 | Furniture/Living Room | Round window |
| **Clock_1_blue.png** | 10x10 | Objects/Bedroom | Wall clock |
| **Clock_1_red.png** | 10x10 | Objects/Bedroom | Wall clock (alt) |
| **Calendar_2.png** | 13x11 | Objects/Bedroom | Wall calendar |
| **Poster_1.png** | 10x13 | Objects/Bedroom | Wall poster |
| **Books_inside_1.png** | 10x4 | Objects/Living Room | Books on shelf |
| **Books_inside_2.png** | 5x4 | Objects/Living Room | Books stack small |
| **Books_outside_1.png** | 7x4 | Objects/Living Room | Books |
| **Books_outside_5.png** | 12x5 | Objects/Living Room | Books row |
| **Flora_aloe.png** | 10x8 | Objects/Living Room | Desk plant |
| **Flora_daisy_4.png** | 10x11 | Objects/Living Room | Potted flower |
| **Flowerpot_medium_green.png** | 7x3 | Objects/Living Room | Pot |
| **Vase_red.png** | 6x6 | Objects/Living Room | Decorative vase |
| **Couch_small_2_blue.png** | 14x12 | Furniture/Living Room | Break area couch |
| **Couch_large_blue.png** | 30x13 | Furniture/Living Room | Lounge couch |
| **Coffee_table_1.png** | 14x7 | Furniture/Living Room | Break room table |
| **Curtain_medium_green.png** | 3x16 | Furniture/Living Room | Window curtain |
| **Curtain_medium_red.png** | 3x16 | Furniture/Living Room | Window curtain |
| **Curtainrail.png** | 14x3 | Furniture/Living Room | Curtain rail |
| **Microwave_white.png** | 9x5 | Objects/Kitchen | Break room |
| **Refrigerator_large_white.png** | 14x23 | Furniture/Kitchen | Break room fridge |
| **Glass_water.png** | 4x3 | Objects/Kitchen | On desk/table |
| **Trophy.png** | 10x7 | Objects/Bedroom | Decoration |

### Background Elements

| Asset | Size | Use |
|---|---|---|
| **Cloud_1.png** | 32x23 | Sky |
| **Cloud_small_3.png** | 15x12 | Sky |
| **House_largel_red.png** | 95x56 | Background building |
| **House_small_beige.png** | 79x40 | Background building |
| **Tree_medium.png** | 36x50 | Outdoor decoration |

### Characters

| Asset | Size | Use |
|---|---|---|
| **Male.png** | 64x48 | 4 frames × 3 rows at 16x16 |
| **Female.png** | 64x48 | 4 frames × 3 rows at 16x16 |

---

## Drawn by PIXI.Graphics (PixelFurniture.ts)

### Already Built

| Component | Function | Description |
|---|---|---|
| Office Desk | `drawOfficeDesk()` | Desk + monitor + keyboard + rolling chair |
| Bulletin Board | `drawBulletinBoard()` | Cork board with pinned papers + sticky notes |
| Building | `drawBuilding()` | Skyline building with lit/unlit windows |
| Elevator | `drawElevator()` | Double-door elevator |
| Water Cooler | `drawWaterCooler()` | Water cooler/dispenser |
| Office Plant | `drawOfficePlant()` | Tall potted plant |
| Whiteboard | `drawWhiteboard()` | Whiteboard with markers |

### Still Missing — Need to Draw

| Component | Description | Priority |
|---|---|---|
| **Server Rack** | Tall rack with blinking lights (for trading floor) | High |
| **Printer/Copier** | Office printer with paper tray | Medium |
| **Wall Monitor** | Large screen showing charts/data (for trading floor) | High |
| **AC Unit** | Wall-mounted air conditioner | Low |
| **Fire Extinguisher** | Small red box on wall | Low |
| **Ceiling Light** | Overhead fluorescent panel | Medium |
| **Door** | Office door (open/closed) | Medium |
| **Trash Bin** | Small bin next to desk | Low |
| **Coffee Machine** | Espresso machine for break area | Medium |
| **Coat Rack** | Near entrance | Low |

---

## Scene Hierarchy

```
Building
├── Exterior
│   ├── Sky (drawn)
│   ├── Clouds (sprites)
│   ├── Skyline buildings (drawn)
│   └── Foundation (drawn)
│
├── Floor 2 — Research Lab
│   ├── Room background (drawn — green striped wall)
│   ├── Wall objects
│   │   ├── Window (sprite)
│   │   ├── Bulletin board (drawn)
│   │   ├── Clock (sprite)
│   │   ├── Shelf + books (sprites)
│   │   └── Ceiling lamp (sprite)
│   ├── Floor objects
│   │   ├── Office desk ×2 (drawn — monitor, chair, keyboard)
│   │   ├── Bookshelf (sprite)
│   │   ├── Lamp (sprite)
│   │   └── Plant (sprite)
│   ├── Elevator (drawn)
│   └── Agents (sprites + walk animation)
│
├── Floor Divider (drawn)
│
└── Floor 1 — Trading Floor
    ├── Room background (drawn — purple textured wall)
    ├── Wall objects
    │   ├── Window (sprite)
    │   ├── Bulletin board (drawn)
    │   ├── Shelf + books (sprites)
    │   └── [Future: Wall monitor]
    ├── Floor objects
    │   ├── Office desk ×2 (drawn)
    │   ├── Drawer (sprite)
    │   ├── Bookshelf (sprite)
    │   └── [Future: Server rack]
    ├── Elevator (drawn)
    └── Agents (sprites + walk animation)
```

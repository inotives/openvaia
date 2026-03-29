# Changelog — feat/gamified-office-v1.3

Branch started: 2026-03-28

## Changes

### Gamified 2D Pixel Office (PixiJS)
- Built 2D side-view office building with PixiJS v8 in Next.js (client-side only via `dynamic` import)
- 2-floor building with rooftop sign ("openVAIA" LED dot-matrix style)
- City skyline background with layered buildings (dark theme)
- Foundation, wall textures (green stripes for F2, purple spots for F1)

### Floor Layout: [Room 50% | Elevator 20% | Room 30%]
- **Floor 1**: Resting Room (left) | Elevator | Research Room (right)
- **Floor 2**: Trading Room (left) | Elevator | Office (right)
- Room divider walls between each section
- Each floor has its own elevator with F-1/F-2 LED indicators

### Pixel Objects (`pixelObjects/`)
- Refactored monolithic `PixelFurniture.ts` into categorized modules:
  - `office.ts` — drawOfficeDesk, drawFilingCabinet, drawMonitor
  - `infrastructure.ts` — drawElevator, drawBuilding, drawDoor, drawDoorLeft
  - `wall.ts` — drawBulletinBoard, drawWhiteboard, drawWallMonitor, drawFloorIndicator, drawRooftopSign
  - `appliances.ts` — drawCoffeeMachine, drawServerRack, drawPrinter, drawWaterCooler, drawTrashBin
  - `decorations.ts` — drawOfficePlant
- Barrel export via `index.ts` for clean imports

### Interactive Elements
- **Doors**: 2D side-view doors that swing open/close on click (scaleX animation)
  - `drawDoor` — hinge on right, swings left
  - `drawDoorLeft` — hinge on left, swings right
- **Elevator buttons**: Up/down call buttons beside each elevator, click to open doors for 3 seconds
- **Elevator doors**: Masked sliding doors with smooth open/close animation

### Sprite Assets Loaded
- 30+ sprite textures loaded: window, bookshelf, bookshelfSmall, table, tableLong, laptop, lamp, cabinet, shelf, clock, plant, books, ceilingLamp, drawer, drawerA, drawerC, couch (blue/red), coffeeTable, fridge, microwave, potGreen, potRed, potSmallGreen, vase, plantDaisy, plantAster, plantAloe, flowerpot

### Agent System
- NPC sprites (male/female) with 4-frame walk animation
- Agents walk randomly within their assigned room bounds
- Click agent to open interaction panel
- Name tags with pixel font below each agent

### Dynamic Room Assignment
- Agents move to rooms based on current activity:
  - In-progress task or chat with "research/search/analyze/find" → Research Room
  - In-progress task or chat with "trad/market/price/crypto/gold" → Trading Room
  - Busy with general work → Office
  - Idle → Resting Room
- Polls every 10s: checks tasks API + agent busy status + recent chat keywords
- Agents teleport to new room when assignment changes

### Room IDs
- `f1_resting`, `f1_research`, `f2_trading`, `f2_office`
- Defined in `officeTypes.ts` as `RoomId` union type
- Each floor returns `FloorRooms` with room bounds for agent placement

### Agent Panel Enhancements
- **Chat**: Stable session ID per agent per day (persists across panel open/close), agent name shown instead of "AGENT"
- **Skills**: Shows all skills with equip/unequip toggle, global skills marked, equipped count
- **Research**: New tab — lists research reports, click to view full report with summary + body
- **Loading**: "Loading ..." indicator when switching tabs

### Architecture Refactor
- `OfficeCanvas.tsx` — React canvas + agent rendering/animation
- `BuildingScene.ts` — skyline, building frame, foundation, wall texture, orchestrates floors
- `Floor1.ts` — Resting room + Research room furniture
- `Floor2.ts` — Trading room + Office furniture
- `ElevatorZone.ts` — Shared elevator zone drawing + button animation
- `officeTypes.ts` — Shared constants, types, utilities, texture loading
- `pixelObjects/` — Categorized drawn furniture components

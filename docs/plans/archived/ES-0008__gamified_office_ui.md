# ES-0008 — Gamified Office UI

## Status: COMPLETE

## Concept

A 2D pixel-art side-view office where agents are visible as animated NPC characters. Agents move between rooms based on their actual activity (researching, trading, working, idle). Click on an agent to interact — chat, view skills, research reports, memory.

## What Was Built

### Building & Rooms

2-floor building with rooftop sign ("openVAIA" LED dot-matrix style), city skyline background, and foundation.

Each floor uses a **[Room 50% | Elevator 20% | Room 30%]** layout:

| Room ID | Floor | Label | Purpose |
|---|---|---|---|
| `f1_resting` | F-1 (left) | Resting | Default room when agent is idle |
| `f1_research` | F-1 (right) | Research | Agent doing research, search, or analysis |
| `f2_trading` | F-2 (left) | Trading | Agent working on trading, markets, or pricing |
| `f2_office` | F-2 (right) | Office | General work (active but no keyword match) |

### Interactive Elements

- **Doors**: 2D side-view doors that swing open/close on click (`drawDoor` — hinge right, `drawDoorLeft` — hinge left)
- **Elevator buttons**: Up/down call buttons beside each elevator, click to open doors for 3 seconds
- **Elevator doors**: Masked sliding doors with smooth open/close animation
- **LED floor indicators**: Dot-matrix displays showing F-1, F-2 above each elevator

### Agent System

- NPC sprites (male/female) with 4-frame walk animation
- Agents walk randomly within their assigned room bounds
- Click agent to open interaction panel
- Name tags with pixel font below each agent

### Dynamic Room Assignment

Polls every 10 seconds and checks:
1. **In-progress tasks** — scans title + tags for keywords
2. **Busy status + recent chat** — if agent is busy (from health API), checks last user message
3. **Keyword mapping**:
   - `research`, `search`, `analyze`, `find` → `f1_research`
   - `trad`, `market`, `price`, `crypto`, `gold` → `f2_trading`
   - Other active work → `f2_office`
   - Idle → `f1_resting`

### Agent Panel

Pixel-styled side panel (desktop) / bottom sheet (mobile) with tabs:

| Tab | Features |
|---|---|
| **Profile** | Stat bars, role, task/memory counts |
| **Chat** | Stable daily session ID, auto-polls every 3s, agent name shown |
| **Skills** | All skills with equip/unequip toggle, global skills marked |
| **Research** | Report list with click-to-view full report (summary + body) |
| **Memory** | Stored memories list |

### Pixel Objects (drawn with PIXI.Graphics)

Organized in `pixelObjects/` directory:
- `office.ts` — drawOfficeDesk, drawFilingCabinet, drawMonitor
- `infrastructure.ts` — drawElevator, drawBuilding, drawDoor, drawDoorLeft
- `wall.ts` — drawBulletinBoard, drawWhiteboard, drawWallMonitor, drawFloorIndicator, drawRooftopSign
- `appliances.ts` — drawCoffeeMachine, drawServerRack, drawPrinter, drawWaterCooler, drawTrashBin
- `decorations.ts` — drawOfficePlant

### Sprite Assets

30+ sprite textures loaded from organized subfolders:
- `ps/furniture/` — bookshelf, table, laptop, cabinet, drawer variants
- `ps/wall/` — window, shelf, clock, ceiling lamp
- `ps/break_room/` — couch (blue/red), coffee table, fridge, microwave
- `ps/decoration/` — books, vase, plants (aster, aloe), pots (green, red, small)
- `ps/npc/` — male and female character sprites

### Architecture

```
ui/src/app/office/
  page.tsx                     — Page wrapper, agent fetching, room assignment logic
  components/
    OfficeCanvas.tsx            — React PixiJS canvas + agent rendering/animation
    BuildingScene.ts            — Skyline, building frame, foundation, wall texture
    Floor1.ts                   — Resting + Research room furniture
    Floor2.ts                   — Trading + Office room furniture
    ElevatorZone.ts             — Shared elevator zone drawing + button animation
    officeTypes.ts              — Constants, types (RoomId, RoomBounds, FloorLayout), texture loading
    AgentPanel.tsx              — Agent interaction panel (profile, chat, skills, research, memory)
    pixelObjects/
      index.ts                  — Barrel export
      office.ts                 — Desk, filing cabinet, monitor
      infrastructure.ts         — Elevator, building, doors
      wall.ts                   — Bulletin board, whiteboard, wall monitor, floor indicator, rooftop sign
      appliances.ts             — Coffee machine, server rack, printer, water cooler, trash bin
      decorations.ts            — Office plant
```

## Design Decisions (Final)

1. **Art style**: Side-view (not top-down) using [Pixel Spaces](https://netherzapdos.itch.io/pixel-spaces) sprite pack + custom PIXI.Graphics drawn objects
2. **Rendering**: PixiJS v8 loaded client-side only via Next.js `dynamic` import with `ssr: false`
3. **Scale**: `S = 4` (4x pixel scaling), canvas 280×125 source pixels
4. **Room assignment**: Driven by task keywords + agent busy status + chat content — no new DB tables needed
5. **Chat sessions**: Stable per-agent per-day ID (`{name}-{YYYY-MM-DD}`) to persist across panel open/close
6. **Floor modularity**: Each floor is a separate file returning `FloorRooms` with room bounds — easy to add new floors
7. **No tilemap editor**: Layout built programmatically in code, not via Tiled — simpler for the side-view approach

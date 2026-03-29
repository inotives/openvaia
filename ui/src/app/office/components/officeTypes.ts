import * as PIXI from "pixi.js";

/** Scale factor — pixelspaces assets are tiny (10-23px), we scale up */
export const S = 4;

/** Canvas dimensions in source pixels */
export const W = 280;
export const H = 125;

/** Building layout constants */
export interface BuildingLayout {
  bldgLeft: number;
  bldgRight: number;
  bldgW: number;
  wallThick: number;
  baseTop: number;
  baseH: number;
  innerLeft: number;
  innerRight: number;
  innerW: number;
}

/** Per-floor layout */
export interface FloorLayout {
  top: number;
  bot: number;
  floorY: number;           // bot - 2 (where objects sit)
  leftRoomLeft: number;     // innerLeft + 2
  elevZoneLeft: number;
  elevZoneRight: number;
  rightRoomLeft: number;    // elevZoneRight + 2
  rightRoomRight: number;   // innerRight - 2
}

/** Room identifiers — used to assign agents to rooms based on task */
export type RoomId =
  | "f1_resting"
  | "f1_research"
  | "f2_trading"
  | "f2_office";

/** Walk bounds for a room (source px) */
export interface RoomBounds {
  id: RoomId;
  label: string;
  minX: number;
  maxX: number;
  y: number;  // floor Y where agents stand
}

/** Return value from floor draw functions */
export interface FloorRooms {
  leftLabel: string;
  rightLabel: string;
  rooms: RoomBounds[];
  elevatorResult?: import("./ElevatorZone").ElevatorZoneResult;
}

/** All loaded textures passed to floor builders */
export interface OfficeTextures {
  window: PIXI.Texture;
  bookshelf: PIXI.Texture;
  table: PIXI.Texture;
  laptop: PIXI.Texture;
  cabinet: PIXI.Texture;
  shelf: PIXI.Texture;
  clock: PIXI.Texture;
  books: PIXI.Texture;
  ceilingLamp: PIXI.Texture;
  couch: PIXI.Texture;
  coffeeTable: PIXI.Texture;
  potGreen: PIXI.Texture;
  vase: PIXI.Texture;
  couch_red: PIXI.Texture;
  fridge: PIXI.Texture;
  microwave: PIXI.Texture;
  bookshelfSmall: PIXI.Texture;
  drawerA: PIXI.Texture;
  drawerC: PIXI.Texture;
  plantAster: PIXI.Texture;
  plantAloe: PIXI.Texture;
  potSmallGreen: PIXI.Texture;
  potRed: PIXI.Texture;
  tableLong: PIXI.Texture;
}

/** Load a texture with nearest-neighbor scaling */
export async function loadTex(path: string): Promise<PIXI.Texture> {
  const t = await PIXI.Assets.load(path);
  t.source.scaleMode = "nearest";
  return t;
}

/** Place a sprite at source-pixel coordinates */
export function place(
  parent: PIXI.Container, tex: PIXI.Texture,
  x: number, y: number, scale = S,
): PIXI.Sprite {
  const s = new PIXI.Sprite(tex);
  s.scale.set(scale);
  s.x = x * S;
  s.y = y * S;
  parent.addChild(s);
  return s;
}

/** Elevator constants */
export const ELEV_W = 18;
export const ELEV_H = 20;
export const WALL_THICK = 3;
export const ELEV_BG_COLOR = 0x3d3647;

/** Load all office textures */
export async function loadAllTextures(): Promise<OfficeTextures> {
  const [windowTex, bookshelfTex, tableTex, laptopTex, cabinetTex,
    shelfTex, clockTex, booksTex, ceilingLampTex,
    couchTex, coffeeTblTex, potGreenTex, vaseTex, couchRedTex,
    fridgeTex, microwaveTex, bookshelfSmallTex, drawerATex, drawerCTex,
    plantAsterTex, plantAloeTex, potSmallGreenTex, potRedTex,
    tableLongTex] = await Promise.all([
    loadTex("/office/ps/wall/window.png"), loadTex("/office/ps/furniture/bookshelf.png"),
    loadTex("/office/ps/furniture/table.png"), loadTex("/office/ps/furniture/laptop.png"),
    loadTex("/office/ps/furniture/cabinet.png"),
    loadTex("/office/ps/wall/shelf.png"), loadTex("/office/ps/wall/clock_blue.png"),
    loadTex("/office/ps/decoration/books_1.png"),
    loadTex("/office/ps/wall/ceiling_lamp.png"),
    loadTex("/office/ps/break_room/couch_blue.png"), loadTex("/office/ps/break_room/coffee_table.png"),
    loadTex("/office/ps/decoration/pot_green.png"), loadTex("/office/ps/decoration/vase.png"),
    loadTex("/office/ps/break_room/couch_red.png"),
    loadTex("/office/ps/break_room/fridge.png"), loadTex("/office/ps/break_room/microwave.png"),
    loadTex("/office/ps/furniture/bookshelf_small.png"),
    loadTex("/office/ps/furniture/drawer_a.png"), loadTex("/office/ps/furniture/drawer_c.png"),
    loadTex("/office/ps/decoration/plant_aster.png"), loadTex("/office/ps/decoration/plant_aloe.png"),
    loadTex("/office/ps/decoration/pot_small_green.png"), loadTex("/office/ps/decoration/pot_red.png"),
    loadTex("/office/ps/furniture/table_long.png"),
  ]);

  return {
    window: windowTex, bookshelf: bookshelfTex, table: tableTex, laptop: laptopTex,
    cabinet: cabinetTex, shelf: shelfTex, clock: clockTex,
    books: booksTex, ceilingLamp: ceilingLampTex,
    couch: couchTex, coffeeTable: coffeeTblTex, potGreen: potGreenTex,
    vase: vaseTex, couch_red: couchRedTex,
    fridge: fridgeTex, microwave: microwaveTex, bookshelfSmall: bookshelfSmallTex,
    drawerA: drawerATex, drawerC: drawerCTex,
    plantAster: plantAsterTex, plantAloe: plantAloeTex,
    potSmallGreen: potSmallGreenTex, potRed: potRedTex,
    tableLong: tableLongTex
  };
}

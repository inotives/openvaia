import * as PIXI from "pixi.js";
import { S, W, H, type BuildingLayout, type FloorLayout, type OfficeTextures, type RoomBounds } from "./officeTypes";
import { drawBuilding, drawRooftopSign } from "./pixelObjects";
import { setupElevatorAnimation } from "./ElevatorZone";
import { drawFloor1 } from "./Floor1";
import { drawFloor2 } from "./Floor2";
/** Building layout constants */
const BLDG_LEFT = 30;
const BLDG_RIGHT = 250;
const BLDG_W = BLDG_RIGHT - BLDG_LEFT;
const WALL_THICK = 3;
const FLOOR2_TOP = 28;
const FLOOR2_BOT = 68;
const FLOOR1_TOP = 71;
const FLOOR1_BOT = 111;
const BASE_TOP = 114;
const BASE_H = 10;

/** Room split: 50% | 20% | 30% */
const ROOM_LEFT_RATIO = 0.50;
const ELEV_ZONE_RATIO = 0.20;

function getBuilding(): BuildingLayout {
  const innerLeft = BLDG_LEFT + WALL_THICK;
  const innerRight = BLDG_RIGHT - WALL_THICK;
  return {
    bldgLeft: BLDG_LEFT, bldgRight: BLDG_RIGHT, bldgW: BLDG_W,
    wallThick: WALL_THICK, baseTop: BASE_TOP, baseH: BASE_H,
    innerLeft, innerRight, innerW: innerRight - innerLeft,
  };
}

function getFloorLayout(bldg: BuildingLayout, top: number, bot: number): FloorLayout {
  const roomLeftW = Math.floor(bldg.innerW * ROOM_LEFT_RATIO);
  const elevZoneW = Math.floor(bldg.innerW * ELEV_ZONE_RATIO);
  const elevZoneLeft = bldg.innerLeft + roomLeftW;
  const elevZoneRight = elevZoneLeft + elevZoneW;
  return {
    top, bot,
    floorY: bot - 2,
    leftRoomLeft: bldg.innerLeft + 2,
    elevZoneLeft, elevZoneRight,
    rightRoomLeft: elevZoneRight + 2,
    rightRoomRight: bldg.innerRight - 2,
  };
}

function drawSkyline(stage: PIXI.Container) {
  const sky = new PIXI.Graphics();
  sky.rect(0, 0, W * S, H * S).fill(0x2c2c3a);
  stage.addChild(sky);

  // Left side — back row (taller, darker)
  drawBuilding(stage, -4, 18, 16, BASE_TOP, 0x2e2e3e, 4, S);
  drawBuilding(stage, 13, 30, 10, BASE_TOP, 0x353548, 3, S);
  // Left side — front row (shorter, lighter)
  drawBuilding(stage, 4, 50, 12, BASE_TOP, 0x42425a, 3, S);
  drawBuilding(stage, 17, 42, 9, BASE_TOP, 0x4a4a62, 2, S);

  // Right side — back row
  drawBuilding(stage, 252, 22, 16, BASE_TOP, 0x2e2e3e, 4, S);
  drawBuilding(stage, 269, 35, 12, BASE_TOP, 0x353548, 3, S);
  // Right side — front row
  drawBuilding(stage, 254, 48, 10, BASE_TOP, 0x42425a, 3, S);
  drawBuilding(stage, 265, 55, 8, BASE_TOP, 0x4a4a62, 2, S);
  drawBuilding(stage, 240, 60, 12, BASE_TOP, 0x3e3e52, 2, S);
}

function drawBuildingFrame(stage: PIXI.Container, bldg: BuildingLayout) {
  const g = new PIXI.Graphics();

  // Outer wall
  g.rect(bldg.bldgLeft * S, FLOOR2_TOP * S, bldg.bldgW * S, (BASE_TOP - FLOOR2_TOP) * S).fill(0x4a4454);

  // Floor 2 interior (green)
  g.rect(bldg.innerLeft * S, (FLOOR2_TOP + WALL_THICK) * S,
    bldg.innerW * S, (FLOOR2_BOT - FLOOR2_TOP - WALL_THICK) * S).fill(0x5daa5a);

  // Floor divider 2→1
  g.rect(bldg.innerLeft * S, FLOOR2_BOT * S,
    bldg.innerW * S, (FLOOR1_TOP - FLOOR2_BOT) * S).fill(0x4a4454);

  // Floor 1 interior (purple)
  g.rect(bldg.innerLeft * S, FLOOR1_TOP * S,
    bldg.innerW * S, (FLOOR1_BOT - FLOOR1_TOP) * S).fill(0xb39ddb);

  // Floor lines (bottom of each room)
  g.rect(bldg.innerLeft * S, (FLOOR2_BOT - 2) * S, bldg.innerW * S, 2 * S).fill(0x555566);
  g.rect(bldg.innerLeft * S, (FLOOR1_BOT - 2) * S, bldg.innerW * S, 2 * S).fill(0x555566);

  stage.addChild(g);
}

function drawWallTexture(stage: PIXI.Container, bldg: BuildingLayout) {
  const g = new PIXI.Graphics();

  // Floor 2 (green): vertical stripes
  for (let i = 0; i < bldg.innerW; i += 3) {
    const shade = i % 6 < 3 ? 0x5daa5a : 0x54a051;
    g.rect((bldg.innerLeft + i) * S, (FLOOR2_TOP + WALL_THICK) * S,
      3 * S, (FLOOR2_BOT - FLOOR2_TOP - WALL_THICK) * S).fill(shade);
  }

  // Floor 1 (purple): subtle texture spots
  for (let i = 0; i < 40; i++) {
    const rx = bldg.innerLeft + Math.random() * bldg.innerW;
    const ry = FLOOR1_TOP + 2 + Math.random() * (FLOOR1_BOT - FLOOR1_TOP - 4);
    g.circle(rx * S, ry * S, S * (0.5 + Math.random())).fill({ color: 0xa88dc4, alpha: 0.3 });
  }

  stage.addChild(g);
}

function drawFoundation(stage: PIXI.Container, bldg: BuildingLayout) {
  const g = new PIXI.Graphics();
  g.rect((bldg.bldgLeft - 3) * S, BASE_TOP * S, (bldg.bldgW + 6) * S, BASE_H * S).fill(0xd4a08a);
  g.rect((bldg.bldgLeft - 3) * S, BASE_TOP * S, (bldg.bldgW + 6) * S, 2 * S).fill(0xba8070);
  stage.addChild(g);
}


function drawRoomLabels(
  stage: PIXI.Container, floor: FloorLayout, bldg: BuildingLayout,
  leftLabel: string, rightLabel: string,
) {
  const ls = { fontFamily: "Pixelify Sans, monospace", fontSize: 14, fill: 0xffffff, letterSpacing: 0.5 };

  // Bias 70% towards elevator side
  const leftCenter = bldg.innerLeft * 0.7 + floor.elevZoneLeft * 0.7;
  const lt = new PIXI.Text({ text: leftLabel, style: ls });
  lt.x = leftCenter * S - lt.width / 2;
  lt.y = (floor.top + 4) * S;
  stage.addChild(lt);

  const rightCenter = floor.elevZoneRight * 0.67 + bldg.innerRight * 0.3;
  const rt = new PIXI.Text({ text: rightLabel, style: ls });
  rt.x = rightCenter * S - rt.width / 2;
  rt.y = (floor.top + 4) * S;
  stage.addChild(rt);
}

/** Build the entire office scene. Returns all room bounds for agent placement. */
export async function buildOfficeScene(
  app: PIXI.Application,
  tex: OfficeTextures,
): Promise<RoomBounds[]> {
  const stage = app.stage;
  const bldg = getBuilding();
  const floor2 = getFloorLayout(bldg, FLOOR2_TOP, FLOOR2_BOT);
  const floor1 = getFloorLayout(bldg, FLOOR1_TOP, FLOOR1_BOT);

  // Background
  drawSkyline(stage);
  drawBuildingFrame(stage, bldg);
  drawRooftopSign(stage, bldg.bldgLeft + bldg.bldgW / 2, FLOOR2_TOP, "openVAIA", S);
  drawFoundation(stage, bldg);
  drawWallTexture(stage, bldg);

  // Floor rooms + furniture (each floor draws its own elevator)
  const f2Result = drawFloor2(stage, floor2, tex);
  const f1Result = drawFloor1(stage, floor1, tex);

  // Setup elevator animations from floor results
  const allElevs = [f2Result, f1Result]
    .map(r => r.elevatorResult)
    .filter((e): e is NonNullable<typeof e> => !!e);
  setupElevatorAnimation(app, allElevs);

  // Room labels
  drawRoomLabels(stage, floor2, bldg, f2Result.leftLabel, f2Result.rightLabel);
  drawRoomLabels(stage, floor1, bldg, f1Result.leftLabel, f1Result.rightLabel);

  return [...f1Result.rooms, ...f2Result.rooms];
}

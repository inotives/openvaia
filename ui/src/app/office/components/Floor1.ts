import * as PIXI from "pixi.js";
import { S, place, type FloorLayout, type FloorRooms, type OfficeTextures } from "./officeTypes";
import { drawOfficeDesk, drawBulletinBoard, drawMonitor, drawServerRack, drawDoor, drawDoorLeft, drawWallMonitor } from "./pixelObjects";
import { drawElevatorZone } from "./ElevatorZone";

/** Draw Floor 1 rooms: Office (left 50%) | Research (right 30%) */
export function drawFloor1(stage: PIXI.Container, floor: FloorLayout, tex: OfficeTextures): FloorRooms {
  const { top, floorY, leftRoomLeft: fLeft, elevZoneLeft, elevZoneRight,
    rightRoomLeft: rrLeft, rightRoomRight: rrRight } = floor;

  // --- Elevator ---
  const elevatorResult = drawElevatorZone(stage, floor, "F-1");

  // --- Resting Room (left 50%) ---
  place(stage, tex.window, fLeft, top + 4);
  place(stage, tex.shelf, fLeft + 15, top + 10);
  place(stage, tex.books, fLeft + 17, top + 7);
  place(stage, tex.couch_red, fLeft, floorY - 12);
  place(stage, tex.couch, fLeft + 30, floorY - 12);
  place(stage, tex.coffeeTable, fLeft + 15, floorY - 7);
  place(stage, tex.plantAster, fLeft + 17, floorY - 23);
  place(stage, tex.vase, fLeft + 19, floorY - 12);

  drawWallMonitor(stage, fLeft + 73, top + 20, S);
  drawBulletinBoard(stage, fLeft + 32, top + 5, S);
  place(stage, tex.tableLong, fLeft + 59, floorY - 7);
  drawDoor(stage, elevZoneLeft+2, floorY, S);

  // --- Research Room (right 30%) ---
  drawDoorLeft(stage, elevZoneRight - 2, floorY, S);
  place(stage, tex.bookshelf, rrRight - 14, top + 15);
  place(stage, tex.bookshelf, rrRight - 29, top + 15);
  place(stage, tex.books, rrRight - 12, top + 17);
  place(stage, tex.books, rrRight - 12, top + 27);
  place(stage, tex.books, rrRight - 12, top + 33);

  place(stage, tex.books, rrRight - 27, top + 17);
  place(stage, tex.books, rrRight - 27, top + 27);
  place(stage, tex.books, rrRight - 27, top + 33);

  place(stage, tex.clock, rrLeft + 49, top + 3);
  place(stage, tex.table, rrLeft + 6, floorY - 7);
  place(stage, tex.laptop, rrLeft + 8, floorY - 14);
  drawServerRack(stage, rrLeft + 26, floorY, S);

  return {
    leftLabel: "Resting",
    rightLabel: "Research",
    rooms: [
      { id: "f1_resting", label: "Resting", minX: fLeft, maxX: elevZoneLeft - 4, y: floorY },
      { id: "f1_research", label: "Research", minX: rrLeft, maxX: rrRight, y: floorY },
    ],
    elevatorResult,
  };
}

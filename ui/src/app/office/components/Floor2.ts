import * as PIXI from "pixi.js";
import { S, place, type FloorLayout, type FloorRooms, type OfficeTextures } from "./officeTypes";
import { drawOfficeDesk, drawBulletinBoard, drawFilingCabinet, drawTrashBin, drawCoffeeMachine, drawDoor, drawDoorLeft, drawServerRack, drawMonitor, drawWallMonitor } from "./pixelObjects";
import { drawElevatorZone } from "./ElevatorZone";

/** Draw Floor 2 rooms: Research Lab (left 50%) | Break Room (right 30%) */
export function drawFloor2(stage: PIXI.Container, floor: FloorLayout, tex: OfficeTextures): FloorRooms {
  const { top, floorY, leftRoomLeft: fLeft, elevZoneLeft, elevZoneRight,
    rightRoomLeft: r2Left, rightRoomRight: r2Right } = floor;

  // --- Elevator ---
  const elevatorResult = drawElevatorZone(stage, floor, "F-2");

  // --- Room 2-1: Trading (left 50%) ---
  place(stage, tex.window, fLeft, top + 4);
  place(stage, tex.coffeeTable, fLeft-1, floorY - 5);
  place(stage, tex.laptop, fLeft+1, floorY - 11);

  drawMonitor(stage, fLeft + 64, floorY - 2, S);
  drawMonitor(stage, fLeft + 81, floorY - 2, S);
  place(stage, tex.table, fLeft + 65, floorY-5);

  drawWallMonitor(stage, fLeft + 66, top + 14, S);
  drawServerRack(stage, fLeft + 20, floorY+2, S);
  drawServerRack(stage, fLeft + 30, floorY+2, S);
  drawServerRack(stage, fLeft + 40, floorY+2, S);
  drawServerRack(stage, fLeft + 50, floorY+2, S);
  drawDoor(stage, elevZoneLeft + 2, floorY, S);

  // --- Room 2-2: Office (right 30%) ---
  drawDoorLeft(stage, elevZoneRight - 2, floorY, S);
  drawBulletinBoard(stage, r2Right - 40, top + 8, S);
  place(stage, tex.clock, r2Right - 8, top + 4);
  drawOfficeDesk(stage, r2Right - 25, floorY+2, S);
  drawOfficeDesk(stage, r2Right - 5, floorY+2, S);
  drawFilingCabinet(stage, r2Right - 40, floorY+2, S);

  return {
    leftLabel: "Trading",
    rightLabel: "Office",
    rooms: [
      { id: "f2_trading", label: "Trading", minX: fLeft, maxX: elevZoneLeft - 4, y: floorY },
      { id: "f2_office", label: "Office", minX: r2Left, maxX: r2Right, y: floorY },
    ],
    elevatorResult,
  };
}

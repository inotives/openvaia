import * as PIXI from "pixi.js";
import { S, ELEV_W, ELEV_H, WALL_THICK, ELEV_BG_COLOR, type FloorLayout } from "./officeTypes";
import { drawElevator, drawFloorIndicator, type ElevatorDoors } from "./pixelObjects";

export interface ElevatorZoneResult {
  doors: ElevatorDoors;
  upBtn: PIXI.Graphics;
  downBtn: PIXI.Graphics;
}

/** Draw elevator zone for a floor: background, elevator, divider walls, indicator, buttons */
/** Draw elevator zone. Optional offsetX/offsetY adjust elevator position within the zone. */
export function drawElevatorZone(
  stage: PIXI.Container, floor: FloorLayout, label: string,
  offsetX = 0, offsetY = 0,
): ElevatorZoneResult {
  const elevZoneW = floor.elevZoneRight - floor.elevZoneLeft;
  const floorH = floor.bot - floor.top;

  // Dark background — extends 3px below to cover floor divider gap
  const bg = new PIXI.Graphics();
  bg.rect((floor.elevZoneLeft + 2) * S, floor.top * S,
    (elevZoneW - 4) * S, (floorH + 3) * S).fill(ELEV_BG_COLOR);
  stage.addChild(bg);

  // Elevator
  const elevLeft = floor.elevZoneLeft + Math.floor((elevZoneW - ELEV_W) / 2) + offsetX;
  const elevBot = floor.bot + offsetY;
  const doors = drawElevator(stage, elevLeft, elevBot, ELEV_W, ELEV_H, S);

  // Divider walls — extend to cover divider gap
  const walls = new PIXI.Graphics();
  walls.rect(floor.elevZoneLeft * S, floor.top * S, 2 * S, (floorH + 3) * S).fill(0x4a4454);
  walls.rect((floor.elevZoneRight - 2) * S, floor.top * S, 2 * S, (floorH + 3) * S).fill(0x4a4454);
  stage.addChild(walls);

  // Floor line
  const floorLine = new PIXI.Graphics();
  floorLine.rect((floor.elevZoneLeft + 2) * S, (floor.bot - 2) * S,
    (elevZoneW - 4) * S, 2 * S).fill(0x555566);
  stage.addChild(floorLine);

  // Floor indicator
  drawFloorIndicator(stage, elevLeft + Math.floor((ELEV_W - 14) / 2), floor.top + WALL_THICK + 2, label, S);

  // Up/Down call buttons
  const btnX = (elevLeft + ELEV_W + 2) * S;
  const btnMidY = (floor.top + floorH * 0.75) * S;
  const btnSize = 2.5 * S;

  const btnPanel = new PIXI.Graphics();
  btnPanel.roundRect(btnX - 1 * S, btnMidY - 4 * S, btnSize + 2 * S, 8 * S, 1 * S).fill(0x888888);
  stage.addChild(btnPanel);

  const upBtn = new PIXI.Graphics();
  upBtn.roundRect(0, 0, btnSize, btnSize, 0.5 * S).fill(0xcccccc);
  upBtn.moveTo(btnSize * 0.5, btnSize * 0.2);
  upBtn.lineTo(btnSize * 0.2, btnSize * 0.7);
  upBtn.lineTo(btnSize * 0.8, btnSize * 0.7);
  upBtn.closePath();
  upBtn.fill(0x444444);
  upBtn.x = btnX;
  upBtn.y = btnMidY - 3.5 * S;
  upBtn.eventMode = "static";
  upBtn.cursor = "pointer";
  stage.addChild(upBtn);

  const downBtn = new PIXI.Graphics();
  downBtn.roundRect(0, 0, btnSize, btnSize, 0.5 * S).fill(0xcccccc);
  downBtn.moveTo(btnSize * 0.5, btnSize * 0.8);
  downBtn.lineTo(btnSize * 0.2, btnSize * 0.3);
  downBtn.lineTo(btnSize * 0.8, btnSize * 0.3);
  downBtn.closePath();
  downBtn.fill(0x444444);
  downBtn.x = btnX;
  downBtn.y = btnMidY + 0.5 * S;
  downBtn.eventMode = "static";
  downBtn.cursor = "pointer";
  stage.addChild(downBtn);

  return { doors, upBtn, downBtn };
}

/** Setup elevator door animation triggered by button clicks */
export function setupElevatorAnimation(app: PIXI.Application, elevs: ElevatorZoneResult[]) {
  elevs.forEach(({ doors, upBtn, downBtn }) => {
    let animTimer = -1;
    const animFrames = 20;
    const holdFrames = 180;
    const totalFrames = animFrames + holdFrames + animFrames;

    const triggerOpen = () => {
      if (animTimer >= 0) return;
      animTimer = 0;
    };

    upBtn.on("pointerdown", triggerOpen);
    downBtn.on("pointerdown", triggerOpen);

    app.ticker.add(() => {
      if (animTimer < 0) return;
      animTimer++;

      let openProgress = 0;
      if (animTimer <= animFrames) {
        openProgress = animTimer / animFrames;
      } else if (animTimer <= animFrames + holdFrames) {
        openProgress = 1;
      } else if (animTimer <= totalFrames) {
        openProgress = 1 - (animTimer - animFrames - holdFrames) / animFrames;
      } else {
        animTimer = -1;
        openProgress = 0;
      }

      doors.leftDoor.x = doors.closedLeftX + (doors.openLeftX - doors.closedLeftX) * openProgress;
      doors.rightDoor.x = doors.closedRightX + (doors.openRightX - doors.closedRightX) * openProgress;
    });
  });
}

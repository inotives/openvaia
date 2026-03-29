import * as PIXI from "pixi.js";

/** Elevator door refs for animation */
export interface ElevatorDoors {
  leftDoor: PIXI.Graphics;
  rightDoor: PIXI.Graphics;
  closedLeftX: number;
  closedRightX: number;
  openLeftX: number;
  openRightX: number;
}

/** Elevator with animated double doors. */
export function drawElevator(parent: PIXI.Container, x: number, floorBot: number, elevW: number, elevH: number, S: number): ElevatorDoors {
  const ey = floorBot - elevH;
  const doorW = (elevW / 2 - 2.5) * S;
  const doorH = (elevH - 4) * S;
  const doorY = (ey + 3) * S;

  const interior = new PIXI.Graphics();
  interior.rect((x + 2) * S, doorY, (elevW - 4) * S, doorH).fill(0x555555);
  parent.addChild(interior);

  const doorContainer = new PIXI.Container();
  const doorMask = new PIXI.Graphics();
  doorMask.rect((x + 2) * S, doorY, (elevW - 4) * S, doorH).fill(0xffffff);
  parent.addChild(doorMask);
  doorContainer.mask = doorMask;

  const closedLeftX = (x + 2) * S;
  const openLeftX = closedLeftX - doorW;
  const leftDoor = new PIXI.Graphics();
  leftDoor.rect(0, 0, doorW, doorH).fill(0xd8d8d8);
  leftDoor.rect(doorW - 1 * S, doorH * 0.45, 0.8 * S, 2 * S).fill(0xaaaaaa);
  leftDoor.x = closedLeftX;
  leftDoor.y = doorY;
  doorContainer.addChild(leftDoor);

  const closedRightX = (x + elevW / 2 + 0.5) * S;
  const openRightX = closedRightX + doorW;
  const rightDoor = new PIXI.Graphics();
  rightDoor.rect(0, 0, doorW, doorH).fill(0xd8d8d8);
  rightDoor.rect(0.2 * S, doorH * 0.45, 0.8 * S, 2 * S).fill(0xaaaaaa);
  rightDoor.x = closedRightX;
  rightDoor.y = doorY;
  doorContainer.addChild(rightDoor);
  parent.addChild(doorContainer);

  const frame = new PIXI.Graphics();
  frame.rect(x * S, ey * S, elevW * S, 3 * S).fill(0xa8a8a8);
  frame.rect(x * S, (ey + elevH - 1) * S, elevW * S, 1 * S).fill(0xa8a8a8);
  frame.rect(x * S, ey * S, 2 * S, elevH * S).fill(0xc8c8c8);
  frame.rect((x + elevW - 2) * S, ey * S, 2 * S, elevH * S).fill(0xc8c8c8);
  frame.rect(x * S, ey * S, elevW * S, elevH * S).stroke({ color: 0x888888, width: S * 0.5 });
  parent.addChild(frame);

  return { leftDoor, rightDoor, closedLeftX, closedRightX, openLeftX, openRightX };
}

/** Tall building with lit/unlit windows for city skyline. */
export function drawBuilding(
  parent: PIXI.Container, x: number, topY: number, w: number, botY: number,
  color: number, winCols: number, S: number,
) {
  const g = new PIXI.Graphics();
  const h = botY - topY;

  g.rect(x * S, topY * S, w * S, h * S).fill(color);
  g.rect(x * S, topY * S, w * S, 2 * S).fill(color + 0x151515);

  const padX = 2;
  const padY = 4;
  const winW = 2;
  const winH = 3;
  const winRows = Math.floor((h - padY * 2) / (winH + 3));
  const gapX = (w - padX * 2 - winW * winCols) / Math.max(winCols - 1, 1);
  const gapY = (h - padY * 2 - winH * winRows) / Math.max(winRows - 1, 1);
  for (let r = 0; r < winRows; r++) {
    for (let c = 0; c < winCols; c++) {
      const lit = Math.random() > 0.35;
      const wx = x + padX + c * (winW + gapX);
      const wy = topY + padY + r * (winH + gapY);
      g.rect(wx * S, wy * S, winW * S, winH * S).fill(lit ? 0xe8d87a : color - 0x101010);
    }
  }

  parent.addChild(g);
}

/** 2D side-view sliding door — thin bar when closed, swings open to show full door face. */
export function drawDoor(parent: PIXI.Container, x: number, y: number, S: number) {
  const u = S;
  const doorH = 18 * u;
  const closedW = 2 * u;
  const openW = 10 * u;
  const px = x * S;
  const py = y * S;

  const door = new PIXI.Graphics();
  door.rect(0, 0, openW, doorH).fill(0x7a5230);
  door.rect(0, 0, openW, 0.5 * u).fill(0x5a3a1a);
  door.rect(0, doorH - 0.5 * u, openW, 0.5 * u).fill(0x5a3a1a);
  door.rect(1 * u, 2 * u, openW - 2 * u, 6 * u).fill(0x8B6B3A);
  door.rect(1 * u, 10 * u, openW - 2 * u, 6 * u).fill(0x8B6B3A);
  door.circle(2 * u, doorH * 0.5, 0.6 * u).fill(0xd4a840);

  door.pivot.set(openW, 0);
  door.x = px;
  door.y = py - doorH;
  door.scale.x = closedW / openW;

  door.eventMode = "static";
  door.cursor = "pointer";

  let isOpen = false;
  let targetScaleX = closedW / openW;

  door.on("pointerdown", () => {
    isOpen = !isOpen;
    targetScaleX = isOpen ? 1 : closedW / openW;
  });

  const ticker = new PIXI.Ticker();
  ticker.add(() => {
    if (door.destroyed) { ticker.stop(); ticker.destroy(); return; }
    const diff = targetScaleX - door.scale.x;
    if (Math.abs(diff) > 0.005) {
      door.scale.x += diff * 0.1;
    } else {
      door.scale.x = targetScaleX;
    }
  });
  ticker.start();

  parent.addChild(door);
}

/** 2D side-view door — hinge on LEFT edge, swings open to the right.
 *  @param x - hinge X in source px (left edge of door)
 *  @param y - bottom Y (floor line) in source px
 */
export function drawDoorLeft(parent: PIXI.Container, x: number, y: number, S: number) {
  const u = S;
  const doorH = 18 * u;
  const closedW = 2 * u;
  const openW = 10 * u;
  const px = x * S;
  const py = y * S;

  const door = new PIXI.Graphics();
  door.rect(0, 0, openW, doorH).fill(0x7a5230);
  door.rect(0, 0, openW, 0.5 * u).fill(0x5a3a1a);
  door.rect(0, doorH - 0.5 * u, openW, 0.5 * u).fill(0x5a3a1a);
  door.rect(1 * u, 2 * u, openW - 2 * u, 6 * u).fill(0x8B6B3A);
  door.rect(1 * u, 10 * u, openW - 2 * u, 6 * u).fill(0x8B6B3A);
  door.circle(openW - 2 * u, doorH * 0.5, 0.6 * u).fill(0xd4a840);

  // Pivot on left edge (hinge), door expands to the right
  door.pivot.set(0, 0);
  door.x = px;
  door.y = py - doorH;
  door.scale.x = closedW / openW;

  door.eventMode = "static";
  door.cursor = "pointer";

  let isOpen = false;
  let targetScaleX = closedW / openW;

  door.on("pointerdown", () => {
    isOpen = !isOpen;
    targetScaleX = isOpen ? 1 : closedW / openW;
  });

  const ticker = new PIXI.Ticker();
  ticker.add(() => {
    if (door.destroyed) { ticker.stop(); ticker.destroy(); return; }
    const diff = targetScaleX - door.scale.x;
    if (Math.abs(diff) > 0.005) {
      door.scale.x += diff * 0.1;
    } else {
      door.scale.x = targetScaleX;
    }
  });
  ticker.start();

  parent.addChild(door);
}

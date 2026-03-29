import * as PIXI from "pixi.js";

/** Water cooler. */
export function drawWaterCooler(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 3*u, py - 2*u, 6*u, 2*u).fill(0x888888);
  g.rect(px - 3*u, py - 12*u, 6*u, 10*u).fill(0xdddddd);
  g.rect(px - 2*u, py - 11*u, 4*u, 4*u).fill(0xcccccc);
  g.rect(px - 2*u, py - 17*u, 4*u, 5*u).fill(0xaaddff);
  g.rect(px - 2*u, py - 17*u, 4*u, 1*u).fill(0x88bbdd);
  g.rect(px + 2*u, py - 7*u, 2*u, 1*u).fill(0x666666);

  parent.addChild(g);
}

/** Server rack with blinking lights. */
export function drawServerRack(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 5*u, py - 24*u, 10*u, 24*u).fill(0x2a2a2a);
  g.rect(px - 4*u, py - 23*u, 8*u, 22*u).fill(0x3a3a3a);
  for (let i = 0; i < 5; i++) {
    const uy = py - 22*u + i * 4.5*u;
    g.rect(px - 3*u, uy, 6*u, 3.5*u).fill(0x444444);
    g.rect(px - 3*u, uy, 6*u, 0.5*u).fill(0x555555);
    const lit1 = Math.random() > 0.3;
    const lit2 = Math.random() > 0.5;
    g.circle(px + 2*u, uy + 1.5*u, 0.8*u).fill(lit1 ? 0x44ff44 : 0x333333);
    g.circle(px + 0*u, uy + 1.5*u, 0.8*u).fill(lit2 ? 0x44aaff : 0x333333);
  }
  g.rect(px - 5*u, py - 24*u, 1*u, 24*u).fill(0x222222);
  g.rect(px + 4*u, py - 24*u, 1*u, 24*u).fill(0x222222);

  parent.addChild(g);
}

/** Office printer/copier. */
export function drawPrinter(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 6*u, py - 8*u, 12*u, 8*u).fill(0xcccccc);
  g.rect(px - 6*u, py - 8*u, 12*u, 1*u).fill(0xdddddd);
  g.rect(px - 5*u, py - 3*u, 10*u, 2*u).fill(0xbbbbbb);
  g.rect(px - 4*u, py - 2.5*u, 8*u, 1*u).fill(0xeeeeee);
  g.rect(px - 5*u, py - 10*u, 10*u, 2*u).fill(0xdddddd);
  g.rect(px - 3*u, py - 6*u, 6*u, 0.5*u).fill(0x333333);
  g.circle(px + 4*u, py - 5*u, 0.8*u).fill(0x44aa44);
  g.rect(px + 2*u, py - 5.5*u, 1.5*u, 1*u).fill(0x888888);

  parent.addChild(g);
}

/** Coffee machine. */
export function drawCoffeeMachine(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 4*u, py - 14*u, 8*u, 14*u).fill(0x333333);
  g.rect(px - 3*u, py - 13*u, 6*u, 5*u).fill(0x444444);
  g.rect(px - 3*u, py - 18*u, 6*u, 4*u).fill(0x88bbdd);
  g.rect(px - 3*u, py - 18*u, 6*u, 1*u).fill(0x6699bb);
  g.rect(px - 2*u, py - 7*u, 4*u, 3*u).fill(0x222222);
  g.rect(px - 1.5*u, py - 4*u, 3*u, 3*u).fill(0xeeeeee);
  g.rect(px - 1*u, py - 3.5*u, 2*u, 1*u).fill(0x6a4a2a);
  g.circle(px + 3*u, py - 10*u, 0.8*u).fill(0xcc4444);
  g.rect(px, py - 5.5*u, 0.5*u, 1.5*u).fill(0x6a4a2a);

  parent.addChild(g);
}

/** Trash bin. */
export function drawTrashBin(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 3*u, py - 6*u, 6*u, 6*u).fill(0x666666);
  g.rect(px - 2.5*u, py - 5*u, 5*u, 4*u).fill(0x777777);
  g.rect(px - 3.5*u, py - 7*u, 7*u, 1*u).fill(0x555555);
  g.rect(px - 1*u, py - 5*u, 0.5*u, 4*u).fill(0x666666);
  g.rect(px + 1*u, py - 5*u, 0.5*u, 4*u).fill(0x666666);

  parent.addChild(g);
}

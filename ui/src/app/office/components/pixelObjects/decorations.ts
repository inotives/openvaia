import * as PIXI from "pixi.js";

/** Potted office plant (tall). */
export function drawOfficePlant(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 3*u, py - 5*u, 6*u, 5*u).fill(0xb5651d);
  g.rect(px - 4*u, py - 5*u, 8*u, 1*u).fill(0xa0550d);
  g.rect(px - 2*u, py - 6*u, 4*u, 1*u).fill(0x5a3a1a);
  g.circle(px, py - 10*u, 5*u).fill(0x3a8a3a);
  g.circle(px - 3*u, py - 8*u, 3*u).fill(0x2d7a2d);
  g.circle(px + 3*u, py - 8*u, 3*u).fill(0x4a9a4a);
  g.circle(px, py - 13*u, 3*u).fill(0x3a8a3a);

  parent.addChild(g);
}

import * as PIXI from "pixi.js";

/** Simple office desk with monitor. */
export function drawOfficeDesk(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 8*u, py - 7*u, 16*u, 2*u).fill(0xB8860B);
  g.rect(px - 8*u, py - 7*u, 16*u, 1*u).fill(0xD4A030);
  g.rect(px - 7*u, py - 5*u, 2*u, 5*u).fill(0x9A6B20);
  g.rect(px + 5*u, py - 5*u, 2*u, 5*u).fill(0x9A6B20);

  g.rect(px - 4*u, py - 13*u, 8*u, 5*u).fill(0x2a2a2a);
  g.rect(px - 3*u, py - 12*u, 6*u, 3*u).fill(0x4488cc);
  g.rect(px - 0.5*u, py - 8*u, 1*u, 1*u).fill(0x333333);
  g.rect(px - 2*u, py - 7*u, 4*u, 0.5*u).fill(0x333333);

  parent.addChild(g);
}

/** Filing cabinet with 3 drawers. */
export function drawFilingCabinet(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;
  const w = 7.5 * u;
  const h = 12 * u;

  g.rect(px - w/2, py - h, w, h).fill(0x2a2a2a);

  const drawerW = w - 2*u;
  const drawerH = 3*u;
  const gap = 0.75*u;
  for (let i = 0; i < 3; i++) {
    const dy = py - h + gap + i * (drawerH + gap);
    g.rect(px - drawerW/2, dy, drawerW, drawerH).fill(0xb0b8c0);
    g.rect(px - drawerW/2, dy, drawerW, 0.5*u).fill(0xc8d0d8);
    g.rect(px - 1*u, dy + drawerH/2 - 0.5*u, 2*u, 1*u).fill(0x666666);
  }

  parent.addChild(g);
}

/** Standalone desk monitor with line chart + bar chart. */
export function drawMonitor(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 8*u, py - 14*u, 16*u, 10*u).fill(0x222222);
  g.rect(px - 7*u, py - 13*u, 14*u, 8*u).fill(0x0e1a28);

  for (let i = 0; i < 3; i++) {
    g.rect(px - 6.5*u, py - 12*u + i * 2.5*u, 6*u, 0.2*u).fill({ color: 0x1a3050, alpha: 0.8 });
  }
  g.moveTo(px - 6.5*u, py - 7*u);
  g.lineTo(px - 5*u, py - 9*u);
  g.lineTo(px - 3.5*u, py - 8*u);
  g.lineTo(px - 2*u, py - 11*u);
  g.lineTo(px - 0.5*u, py - 10*u);
  g.stroke({ color: 0x44dd44, width: u * 0.5 });

  const bars = [3, 5, 4, 6, 3.5, 5.5];
  const barW = 0.8 * u;
  const barGap = 0.4 * u;
  const barStartX = px + 0.5*u;
  const barBaseY = py - 6*u;
  bars.forEach((h, i) => {
    const bx = barStartX + i * (barW + barGap);
    const color = i % 2 === 0 ? 0x4488cc : 0x44bbdd;
    g.rect(bx, barBaseY - h*u, barW, h*u).fill(color);
  });

  g.rect(px - 0.5*u, py - 4*u, 1*u, 2*u).fill(0x333333);
  g.rect(px - 3*u, py - 2*u, 6*u, 1*u).fill(0x333333);

  parent.addChild(g);
}

import * as PIXI from "pixi.js";

/** Bulletin/cork board with pinned papers and sticky notes. */
export function drawBulletinBoard(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px, py, 22*u, 14*u).fill(0x2a2a2a);
  g.rect(px + 1*u, py + 1*u, 20*u, 12*u).fill(0xa07840);

  g.rect(px + 2*u, py + 2*u, 5*u, 4*u).fill(0xeeeeee);
  g.rect(px + 3*u, py + 3*u, 3*u, 2*u).fill(0x888888);

  g.rect(px + 8*u, py + 2*u, 5*u, 5*u).fill(0xd4a030);
  g.rect(px + 9*u, py + 3*u, 3*u, 3*u).fill(0xc48820);

  g.rect(px + 14*u, py + 2*u, 6*u, 4*u).fill(0xeeeeee);
  g.rect(px + 15*u, py + 3*u, 4*u, 1*u).fill(0x888888);
  g.rect(px + 15*u, py + 4.5*u, 4*u, 1*u).fill(0x888888);

  g.rect(px + 2*u, py + 7*u, 3*u, 3*u).fill(0xe8d44a);
  g.rect(px + 6*u, py + 7*u, 3*u, 3*u).fill(0x4488dd);

  g.rect(px + 10*u, py + 8*u, 5*u, 3*u).fill(0xbbbbbb);
  g.rect(px + 11*u, py + 9*u, 3*u, 1*u).fill(0x999999);

  parent.addChild(g);
}

/** Whiteboard on wall. */
export function drawWhiteboard(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px, py, 24*u, 14*u).fill(0x888888);
  g.rect(px + 1*u, py + 1*u, 22*u, 12*u).fill(0xf5f5f5);
  g.rect(px + 3*u, py + 3*u, 8*u, 1*u).fill(0x3355aa);
  g.rect(px + 3*u, py + 5*u, 12*u, 1*u).fill(0x3355aa);
  g.rect(px + 3*u, py + 7*u, 6*u, 1*u).fill(0xcc4444);
  g.rect(px + 3*u, py + 9*u, 10*u, 1*u).fill(0x3355aa);
  g.rect(px + 2*u, py + 12*u, 20*u, 1*u).fill(0x999999);
  g.rect(px + 14*u, py + 11*u, 2*u, 1*u).fill(0xcc4444);
  g.rect(px + 17*u, py + 11*u, 2*u, 1*u).fill(0x3355aa);

  parent.addChild(g);
}

/** Wall-mounted monitor showing charts/data. */
export function drawWallMonitor(parent: PIXI.Container, x: number, y: number, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px - 10*u, py - 7*u, 20*u, 14*u).fill(0x222222);
  g.rect(px - 9*u, py - 6*u, 18*u, 12*u).fill(0x1a2a3a);
  g.moveTo(px - 8*u, py + 3*u);
  g.lineTo(px - 5*u, py + 1*u);
  g.lineTo(px - 2*u, py + 2*u);
  g.lineTo(px + 1*u, py - 2*u);
  g.lineTo(px + 4*u, py - 1*u);
  g.lineTo(px + 7*u, py - 4*u);
  g.stroke({ color: 0x44dd44, width: u * 0.8 });
  g.moveTo(px - 8*u, py + 2*u);
  g.lineTo(px - 4*u, py + 3*u);
  g.lineTo(px + 0*u, py + 1*u);
  g.lineTo(px + 4*u, py + 2*u);
  g.lineTo(px + 7*u, py - 1*u);
  g.stroke({ color: 0xdd4444, width: u * 0.5 });
  for (let i = 0; i < 3; i++) {
    g.rect(px - 8*u, (py - 4 + i * 3) * u, 16*u, 0.3*u).fill({ color: 0x335566, alpha: 0.5 });
  }
  g.rect(px - 8*u, py + 4*u, 4*u, 1*u).fill(0x44dd44);
  g.rect(px - 2*u, py + 4*u, 3*u, 1*u).fill(0xdd4444);

  parent.addChild(g);
}

/** LED dot-matrix floor indicator. */
export function drawFloorIndicator(parent: PIXI.Container, x: number, y: number, label: string, S: number) {
  const g = new PIXI.Graphics();
  const px = x * S;
  const py = y * S;
  const u = S;

  g.rect(px, py, 14*u, 9*u).fill(0xaaaaaa);
  g.rect(px + 0.5*u, py + 0.5*u, 13*u, 8*u).fill(0xc0c0c0);
  g.rect(px + 1*u, py + 1*u, 12*u, 7*u).fill(0x111118);

  const FONT: Record<string, number[][]> = {
    "F": [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,0,0]],
    "-": [[0,0,0],[0,0,0],[1,1,1],[0,0,0],[0,0,0]],
    "1": [[0,1,0],[1,1,0],[0,1,0],[0,1,0],[1,1,1]],
    "2": [[1,1,1],[0,0,1],[1,1,1],[1,0,0],[1,1,1]],
    "3": [[1,1,1],[0,0,1],[1,1,1],[0,0,1],[1,1,1]],
  };

  const dotSize = 0.8 * u;
  const charW = 3;
  const charH = 5;
  const gap = 1;
  const totalDotsW = label.length * charW + (label.length - 1) * gap;
  const startX = px + 1*u + (12*u - totalDotsW * dotSize) / 2;
  const startY = py + 1*u + (7*u - charH * dotSize) / 2;

  for (let ci = 0; ci < label.length; ci++) {
    const ch = FONT[label[ci]];
    if (!ch) continue;
    const ox = startX + ci * (charW + gap) * dotSize;
    for (let row = 0; row < charH; row++) {
      for (let col = 0; col < charW; col++) {
        const dx = ox + col * dotSize;
        const dy = startY + row * dotSize;
        if (ch[row][col]) {
          g.circle(dx + dotSize/2, dy + dotSize/2, dotSize * 0.4).fill(0xff2222);
          g.circle(dx + dotSize/2, dy + dotSize/2, dotSize * 0.5).fill({ color: 0xff4444, alpha: 0.3 });
        } else {
          g.circle(dx + dotSize/2, dy + dotSize/2, dotSize * 0.25).fill({ color: 0x331111, alpha: 0.5 });
        }
      }
    }
  }

  parent.addChild(g);
}

/** Pixel rooftop sign board. */
export function drawRooftopSign(parent: PIXI.Container, x: number, y: number, text: string, S: number) {
  const g = new PIXI.Graphics();
  const u = S * 1.3;
  const signW = (text.length * 5 + 6) * u;
  const signH = 9 * u;
  const postH = 5 * u;
  const px = x * S - signW / 2;
  const py = (y * S) - postH - signH;

  const postW = 2 * u;
  g.rect(px + signW * 0.25 - postW / 2, py + signH, postW, postH).fill(0x222222);
  g.rect(px + signW * 0.75 - postW / 2, py + signH, postW, postH).fill(0x222222);

  g.rect(px, py, signW, signH).fill(0x1a1a1a);
  g.rect(px + u, py + u, signW - 2 * u, signH - 2 * u).fill(0xcc2222);

  const FONT: Record<string, number[][]> = {
    "o": [[0,1,0],[1,0,1],[1,0,1],[1,0,1],[0,1,0]],
    "p": [[1,1,0],[1,0,1],[1,1,0],[1,0,0],[1,0,0]],
    "e": [[1,1,1],[1,0,0],[1,1,0],[1,0,0],[1,1,1]],
    "n": [[1,0,1],[1,1,1],[1,0,1],[1,0,1],[1,0,1]],
    "V": [[1,0,1],[1,0,1],[1,0,1],[0,1,0],[0,1,0]],
    "A": [[0,1,0],[1,0,1],[1,1,1],[1,0,1],[1,0,1]],
    "I": [[1,1,1],[0,1,0],[0,1,0],[0,1,0],[1,1,1]],
  };

  const dotSize = u;
  const charW = 3;
  const charH = 5;
  const gap = 1;
  const totalW = text.length * charW + (text.length - 1) * gap;
  const startX = px + (signW - totalW * dotSize) / 2;
  const startY = py + (signH - charH * dotSize) / 2;

  for (let ci = 0; ci < text.length; ci++) {
    const ch = FONT[text[ci]];
    if (!ch) continue;
    const ox = startX + ci * (charW + gap) * dotSize;
    for (let row = 0; row < charH; row++) {
      for (let col = 0; col < charW; col++) {
        if (ch[row][col]) {
          g.rect(ox + col * dotSize, startY + row * dotSize, dotSize * 0.9, dotSize * 0.9).fill(0xffffff);
        }
      }
    }
  }

  parent.addChild(g);
}

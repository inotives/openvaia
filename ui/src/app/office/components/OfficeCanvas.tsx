"use client";

import React, { useEffect, useRef } from "react";
import * as PIXI from "pixi.js";
import { S, W, H, loadTex, loadAllTextures, type RoomBounds, type RoomId } from "./officeTypes";
import { buildOfficeScene } from "./BuildingScene";

const DEFAULT_ROOM: RoomId = "f1_resting";

interface AgentData {
  name: string; role: string; status: string;
  healthy: boolean | null; last_seen: string | null; skill_count: number;
}

interface Props {
  agents: AgentData[];
  agentRooms: Record<string, string>;
  selectedAgent: string | null;
  onSelectAgent: (name: string) => void;
}

export default function OfficeCanvas({ agents, agentRooms, selectedAgent, onSelectAgent }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const appRef = useRef<PIXI.Application | null>(null);
  const readyRef = useRef(false);
  const agentsRef = useRef<Map<string, PIXI.Container>>(new Map());
  const agentRoomRef = useRef<Map<string, string>>(new Map());
  const agentBoundsRef = useRef<Map<string, RoomBounds>>(new Map());
  const roomsRef = useRef<RoomBounds[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;
    let cancelled = false;

    // Clean up any previous canvas
    containerRef.current.innerHTML = "";
    if (appRef.current) {
      try { appRef.current.destroy(true, { children: true }); } catch {}
      appRef.current = null;
    }

    const app = new PIXI.Application();

    (async () => {
      await app.init({
        width: W * S, height: H * S,
        backgroundColor: 0x2c2c3a,
        resolution: 1, antialias: false,
        autoDensity: false, resizeTo: undefined as any,
      });

      if (cancelled || !containerRef.current) {
        try { app.destroy(true); } catch {}
        return;
      }

      containerRef.current.innerHTML = "";
      const c = app.canvas;
      c.style.maxWidth = "100%";
      c.style.maxHeight = "100%";
      c.style.width = "auto";
      c.style.height = "auto";
      c.style.imageRendering = "pixelated";
      containerRef.current.appendChild(c);

      appRef.current = app;
      const tex = await loadAllTextures();
      roomsRef.current = await buildOfficeScene(app, tex);
      readyRef.current = true;
    })();

    return () => {
      cancelled = true;
      if (appRef.current) {
        try { appRef.current.destroy(true, { children: true }); } catch {}
        appRef.current = null;
        readyRef.current = false;
        agentsRef.current.clear();
        roomsRef.current = [];
      }
    };
  }, []);

  useEffect(() => {
    if (!appRef.current || !readyRef.current) {
      const t = setTimeout(() => {
        if (appRef.current && readyRef.current)
          renderAgents(appRef.current, agents, selectedAgent, onSelectAgent);
      }, 600);
      return () => clearTimeout(t);
    }
    renderAgents(appRef.current, agents, selectedAgent, onSelectAgent);
  }, [agents, agentRooms, selectedAgent, onSelectAgent]);

  async function renderAgents(
    app: PIXI.Application, agents: AgentData[],
    selected: string | null, onSelect: (name: string) => void,
  ) {
    const maleTex = await loadTex("/office/ps/npc/male.png");
    const femaleTex = await loadTex("/office/ps/npc/female.png");

    const AGENT_NPC: Record<string, PIXI.Texture> = {
      "robin": maleTex,
      "ino": femaleTex,
    };

    const rooms = roomsRef.current;
    if (!rooms.length) return;
    const fallbackRoom = rooms.find(r => r.id === DEFAULT_ROOM) || rooms[0];

    // Resolve room for each agent from agentRooms prop
    const getRoom = (name: string) => agentRooms[name] || DEFAULT_ROOM;

    agents.forEach((agent, i) => {
      const roomId = getRoom(agent.name);
      const room = rooms.find(r => r.id === roomId) || fallbackRoom;
      if (!room) return;
      const bounds = room;
      // Spread agents within the room
      const roommates = agents.filter(a => getRoom(a.name) === roomId);
      const spread = (room.maxX - room.minX) / (roommates.length + 1);
      const roomAgentIdx = roommates.indexOf(agent);
      const startX = room.minX + spread * (roomAgentIdx + 1);
      const pos = { x: startX, y: room.y };
      let ct = agentsRef.current.get(agent.name);

      // Check if agent changed rooms — teleport to new room
      const prevRoom = agentRoomRef.current.get(agent.name);
      if (ct && prevRoom && prevRoom !== roomId) {
        ct.x = pos.x * S;
        ct.y = pos.y * S;
      }
      agentRoomRef.current.set(agent.name, roomId);
      agentBoundsRef.current.set(agent.name, room);

      if (!ct) {
        ct = new PIXI.Container();
        ct.x = pos.x * S;
        ct.y = pos.y * S;
        ct.eventMode = "static";
        ct.cursor = "pointer";
        ct.on("pointerdown", () => onSelect(agent.name));

        // NPC sprite — walk frames from row 0 (4 frames, 16x16 each)
        const tex = AGENT_NPC[agent.name] || maleTex;
        const frames: PIXI.Texture[] = [];
        for (let f = 0; f < 4; f++) {
          frames.push(new PIXI.Texture({
            source: tex.source,
            frame: new PIXI.Rectangle(f * 16, 0, 16, 16),
          }));
        }

        const npcSprite = new PIXI.Sprite(frames[0]);
        const npcScale = S;
        npcSprite.scale.set(npcScale);
        npcSprite.anchor.set(0.5, 1);
        ct.addChild(npcSprite);

        // Name tag
        const nt = new PIXI.Text({
          text: agent.name,
          style: { fontFamily: "Pixelify Sans, monospace", fontSize: 10, fill: 0xffffff, letterSpacing: 0.5 },
        });
        nt.anchor.set(0.5, 0);
        nt.y = 4;

        const bg = new PIXI.Graphics();
        bg.roundRect(-nt.width / 2 - 4, 2, nt.width + 8, 14, 3).fill({ color: 0x000000, alpha: 0.6 });
        ct.addChild(bg);
        ct.addChild(nt);


        app.stage.addChild(ct);
        agentsRef.current.set(agent.name, ct);

        // Walking animation
        let targetX = pos.x * S;
        let walkTimer = 0;
        let idleTime = 60 + Math.random() * 120;
        let frameIdx = 0;
        let frameTimer = 0;
        let walking = false;
        const speed = 0.5 * S;

        app.ticker.add(() => {
          if (!ct) return;
          // Use dynamic bounds (room may change)
          const curBounds = agentBoundsRef.current.get(agent.name) || bounds;

          if (!walking) {
            npcSprite.texture = frames[0];
            walkTimer++;
            if (walkTimer >= idleTime) {
              targetX = (curBounds.minX + Math.random() * (curBounds.maxX - curBounds.minX)) * S;
              walking = true;
              walkTimer = 0;
            }
          } else {
            const dx = targetX - ct.x;
            if (Math.abs(dx) < speed) {
              ct.x = targetX;
              walking = false;
              idleTime = 60 + Math.random() * 180;
              npcSprite.texture = frames[0];
            } else {
              ct.x += dx > 0 ? speed : -speed;
              npcSprite.scale.x = dx > 0 ? npcScale : -npcScale;
              frameTimer++;
              if (frameTimer > 8) {
                frameTimer = 0;
                frameIdx = (frameIdx + 1) % frames.length;
                npcSprite.texture = frames[frameIdx];
              }
            }
          }
        });
      }

      if (ct) ct.alpha = selected && selected !== agent.name ? 0.35 : 1;
    });
  }

  return (
    <div ref={containerRef} style={{
      width: "100%", height: "100%",
      display: "flex", alignItems: "center", justifyContent: "center",
      paddingTop: 40,
      backgroundColor: "#2c2c3a",
      overflow: "hidden",
    }} />
  );
}

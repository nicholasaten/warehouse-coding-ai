"use client";

import { useMemo, useRef, useState } from "react";

import { apiJson, ApiError } from "@/lib/api-client";
import type { Location } from "@/lib/types";

const DEFAULT_WIDTH = 140;
const DEFAULT_HEIGHT = 70;
const MIN_WIDTH = 48;
const MIN_HEIGHT = 32;
const GRID_COLUMNS = 5;
const GRID_GAP = 16;
const CANVAS_PADDING = 24;

type Box = { x: number; y: number; width: number; height: number };

/** For any Location that's never been placed on the canvas (layout_x is
 * null), arranges it into a simple left-to-right grid so it's visible
 * and draggable from somewhere sane, rather than stacking every unplaced
 * box at (0,0). Placed locations keep whatever position/size an admin
 * already dragged them to. */
function initialBoxes(locations: Location[]): Record<string, Box> {
  const boxes: Record<string, Box> = {};
  let unplacedIndex = 0;
  for (const loc of locations) {
    if (loc.layout_x !== null && loc.layout_y !== null && loc.layout_width !== null && loc.layout_height !== null) {
      boxes[loc.id] = { x: loc.layout_x, y: loc.layout_y, width: loc.layout_width, height: loc.layout_height };
    } else {
      const col = unplacedIndex % GRID_COLUMNS;
      const row = Math.floor(unplacedIndex / GRID_COLUMNS);
      boxes[loc.id] = {
        x: CANVAS_PADDING + col * (DEFAULT_WIDTH + GRID_GAP),
        y: CANVAS_PADDING + row * (DEFAULT_HEIGHT + GRID_GAP),
        width: DEFAULT_WIDTH,
        height: DEFAULT_HEIGHT,
      };
      unplacedIndex += 1;
    }
  }
  return boxes;
}

export function LayoutCanvas({ locations }: { locations: Location[] }) {
  const [boxes, setBoxes] = useState<Record<string, Box>>(() => initialBoxes(locations));
  const [activeId, setActiveId] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const dragState = useRef<{ id: string; mode: "move" | "resize"; startX: number; startY: number; box: Box } | null>(
    null,
  );

  const { canvasWidth, canvasHeight } = useMemo(() => {
    let maxX = 800;
    let maxY = 500;
    for (const box of Object.values(boxes)) {
      maxX = Math.max(maxX, box.x + box.width + CANVAS_PADDING);
      maxY = Math.max(maxY, box.y + box.height + CANVAS_PADDING);
    }
    return { canvasWidth: maxX, canvasHeight: maxY };
  }, [boxes]);

  async function persist(id: string, box: Box) {
    setSavingId(id);
    setError(null);
    try {
      await apiJson(`/locations/${id}/layout`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          layout_x: box.x,
          layout_y: box.y,
          layout_width: box.width,
          layout_height: box.height,
        }),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the layout.");
    } finally {
      setSavingId(null);
    }
  }

  function handlePointerDown(e: React.PointerEvent, id: string, mode: "move" | "resize") {
    e.stopPropagation();
    try {
      (e.target as Element).setPointerCapture(e.pointerId);
    } catch {
      // Not every input source (or test environment) supports capture --
      // dragging still works via the bubbled move/up listeners below, it
      // just won't keep tracking if the pointer leaves the element's box.
    }
    dragState.current = { id, mode, startX: e.clientX, startY: e.clientY, box: boxes[id] };
    setActiveId(id);
  }

  function handlePointerMove(e: React.PointerEvent) {
    const drag = dragState.current;
    if (!drag) return;
    const dx = e.clientX - drag.startX;
    const dy = e.clientY - drag.startY;
    setBoxes((prev) => {
      const base = drag.box;
      const next: Box =
        drag.mode === "move"
          ? { ...base, x: Math.max(0, base.x + dx), y: Math.max(0, base.y + dy) }
          : { ...base, width: Math.max(MIN_WIDTH, base.width + dx), height: Math.max(MIN_HEIGHT, base.height + dy) };
      return { ...prev, [drag.id]: next };
    });
  }

  function handlePointerUp() {
    const drag = dragState.current;
    dragState.current = null;
    setActiveId(null);
    if (!drag) return;
    const finalBox = boxes[drag.id];
    if (finalBox) void persist(drag.id, finalBox);
  }

  if (locations.length === 0) {
    return <p className="text-sm text-ink-dim">No locations in this warehouse yet.</p>;
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-ink-dim">
        <span>Drag a box to move it, drag its bottom-right corner to resize. Changes save automatically.</span>
        {savingId && <span className="text-accent">Saving…</span>}
      </div>
      {error && <p className="text-sm text-status-critical">{error}</p>}
      <div className="overflow-auto rounded-card border border-line bg-paper/60" style={{ maxHeight: "70vh" }}>
        <div
          className="relative"
          style={{
            width: canvasWidth,
            height: canvasHeight,
            backgroundImage: "radial-gradient(var(--line) 1px, transparent 1px)",
            backgroundSize: "20px 20px",
          }}
        >
          {locations.map((loc) => {
            const box = boxes[loc.id];
            if (!box) return null;
            const isActive = activeId === loc.id;
            return (
              <div
                key={loc.id}
                onPointerDown={(e) => handlePointerDown(e, loc.id, "move")}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                className="absolute flex select-none flex-col justify-center overflow-hidden rounded-md border bg-card px-2 py-1 shadow-sm"
                style={{
                  left: box.x,
                  top: box.y,
                  width: box.width,
                  height: box.height,
                  cursor: "grab",
                  zIndex: isActive ? 10 : 1,
                  borderColor: isActive ? "var(--accent)" : "var(--line-strong)",
                }}
              >
                <p className="truncate font-mono text-[11px] font-semibold text-ink">{loc.generated_code}</p>
                <p className="truncate text-[10px] text-ink-dim">{loc.description}</p>
                <div
                  onPointerDown={(e) => handlePointerDown(e, loc.id, "resize")}
                  onPointerMove={handlePointerMove}
                  onPointerUp={handlePointerUp}
                  className="absolute bottom-0 right-0 h-3 w-3"
                  style={{ cursor: "nwse-resize", background: "var(--line-strong)" }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

"use client";

import { Plus, Trash2 } from "lucide-react";
import { getTypographyClassName } from "../../../config/typography.ts";
import { cn } from "../../../utils/cn.ts";
import { OCCUPANCY_BASIS_OPTIONS } from "../../product/rates/types.ts";
import type { RoomAllocation } from "../types.ts";

/** `RoomAllocation` plus a stable client-side id — `TripProfile.room_config` has no natural
 * identifier, and this list can be reordered/added/removed, so we mint one for `key=` instead
 * of using the array index (repo convention: never `key={index}` on a mutable list). */
export type EditableRoomAllocation = RoomAllocation & { _id: string };

let roomIdCounter = 0;
export function newEditableRoomId(): string {
  roomIdCounter += 1;
  return `room-${Date.now()}-${roomIdCounter}`;
}

export function withRoomIds(rooms: RoomAllocation[]): EditableRoomAllocation[] {
  return rooms.map((room) => ({ ...room, _id: newEditableRoomId() }));
}

export function stripRoomIds(rooms: EditableRoomAllocation[]): RoomAllocation[] {
  return rooms.map((room) => ({
    room_type: room.room_type,
    count: room.count,
    extra_bed: room.extra_bed,
    occupants_note: room.occupants_note,
  }));
}

export interface RoomConfigEditorProps {
  rooms: EditableRoomAllocation[];
  onChange: (rooms: EditableRoomAllocation[]) => void;
}

const inputClass = cn(
  getTypographyClassName("bodySm"),
  "h-8 rounded-[var(--radius-button)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 text-[var(--color-on-surface)]",
);

/** Editable room-allocation list inside the TripProfile review gate (15.7 §2). */
export function RoomConfigEditor({ rooms, onChange }: RoomConfigEditorProps) {
  const updateRoom = (id: string, patch: Partial<RoomAllocation>) => {
    onChange(rooms.map((room) => (room._id === id ? { ...room, ...patch } : room)));
  };

  const removeRoom = (id: string) => {
    onChange(rooms.filter((room) => room._id !== id));
  };

  const addRoom = () => {
    onChange([...rooms, { _id: newEditableRoomId(), room_type: "dbl", count: 1, extra_bed: false, occupants_note: null }]);
  };

  return (
    <div className="flex flex-col gap-2">
      <span className={cn(getTypographyClassName("label"), "text-[var(--color-muted)]")}>Room configuration</span>
      {rooms.map((room) => (
        <div key={room._id} className="grid grid-cols-[auto_auto_auto_1fr_auto] items-center gap-2">
          <select value={room.room_type} onChange={(event) => updateRoom(room._id, { room_type: event.target.value })} className={inputClass}>
            {OCCUPANCY_BASIS_OPTIONS.map((basis) => (
              <option key={basis} value={basis}>
                {basis}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            value={room.count}
            onChange={(event) => updateRoom(room._id, { count: Math.max(1, Number(event.target.value) || 1) })}
            className={cn(inputClass, "w-16")}
          />
          <label className={cn(getTypographyClassName("caption"), "flex items-center gap-1 text-[var(--color-muted)]")}>
            <input type="checkbox" checked={room.extra_bed} onChange={(event) => updateRoom(room._id, { extra_bed: event.target.checked })} />
            extra bed
          </label>
          <input
            type="text"
            value={room.occupants_note ?? ""}
            placeholder="occupants note"
            onChange={(event) => updateRoom(room._id, { occupants_note: event.target.value || null })}
            className={inputClass}
          />
          <button
            type="button"
            onClick={() => removeRoom(room._id)}
            className="rounded-full p-1 text-[var(--color-muted)] hover:bg-[var(--color-surface-muted)] hover:text-rose-600 cursor-pointer"
            aria-label="Remove room"
          >
            <Trash2 size={13} aria-hidden="true" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addRoom}
        className={cn(
          getTypographyClassName("buttonSecondary"),
          "flex w-fit items-center gap-1 rounded-[var(--radius-button)] border border-dashed border-[var(--color-border-strong)] px-2.5 py-1.5 text-[var(--color-accent)] hover:bg-[var(--color-accent-wash)] cursor-pointer",
        )}
      >
        <Plus size={12} aria-hidden="true" />
        <span>Add room</span>
      </button>
    </div>
  );
}

export default RoomConfigEditor;

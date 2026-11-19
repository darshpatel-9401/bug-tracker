import { useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { PRIORITY_STYLES, STATUSES, TYPE_STYLES, initials, label } from "../constants";

function TicketCardBody({ ticket, floating = false }) {
  return (
    <div
      className={`rounded-md border border-line bg-white p-3 text-left shadow-sm ${
        floating ? "rotate-1 border-signal shadow-lg" : "hover:border-ink"
      }`}
    >
      <div className="mb-1 flex items-center justify-between font-mono text-xs">
        <span className="text-muted">#{ticket.id}</span>
        <span className={`font-medium uppercase ${TYPE_STYLES[ticket.type]}`}>{label(ticket.type)}</span>
      </div>
      <p className="text-sm font-medium leading-snug">{ticket.title}</p>
      <div className="mt-3 flex items-center justify-between">
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${PRIORITY_STYLES[ticket.priority]}`}>
          {ticket.priority}
        </span>
        {ticket.assignee ? (
          <span
            title={ticket.assignee.full_name}
            className="flex h-6 w-6 items-center justify-center rounded-full bg-ink font-mono text-[10px] text-paper"
          >
            {initials(ticket.assignee.full_name)}
          </span>
        ) : (
          <span className="text-xs text-muted">Unassigned</span>
        )}
      </div>
    </div>
  );
}

function DraggableTicket({ ticket, canEdit, onOpen }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: ticket.id,
    disabled: !canEdit,
  });
  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={() => onOpen(ticket)}
      className={`cursor-pointer ${isDragging ? "opacity-30" : ""}`}
    >
      <TicketCardBody ticket={ticket} />
    </div>
  );
}

function Column({ status, tickets, canEdit, onOpen, onAdd }) {
  const { setNodeRef, isOver } = useDroppable({ id: status.id });
  return (
    <section
      ref={setNodeRef}
      className={`flex min-h-[320px] flex-col rounded-lg border bg-stone-100/70 p-2 transition ${
        isOver ? "border-signal bg-orange-50" : "border-line"
      }`}
    >
      <header className="mb-2 flex items-center justify-between px-1">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">
          {status.label} <span className="ml-1 font-mono">{tickets.length}</span>
        </h3>
        {canEdit && (
          <button
            className="rounded px-1.5 text-lg leading-none text-muted hover:bg-stone-200 hover:text-ink"
            title={`Add a ticket to ${status.label}`}
            onClick={() => onAdd(status.id)}
          >
            +
          </button>
        )}
      </header>
      <div className="flex flex-1 flex-col gap-2">
        {tickets.map((ticket) => (
          <DraggableTicket key={ticket.id} ticket={ticket} canEdit={canEdit} onOpen={onOpen} />
        ))}
      </div>
    </section>
  );
}

export default function KanbanBoard({ tickets, canEdit, onMove, onOpen, onAdd }) {
  const [activeTicket, setActiveTicket] = useState(null);
  // A small drag distance lets a plain click open the ticket instead of starting a drag.
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  function handleDragEnd({ active, over }) {
    setActiveTicket(null);
    if (!over) return;
    const ticket = tickets.find((t) => t.id === active.id);
    if (ticket && ticket.status !== over.id) onMove(ticket.id, over.id);
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={({ active }) => setActiveTicket(tickets.find((t) => t.id === active.id) || null)}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveTicket(null)}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {STATUSES.map((status) => (
          <Column
            key={status.id}
            status={status}
            tickets={tickets.filter((t) => t.status === status.id)}
            canEdit={canEdit}
            onOpen={onOpen}
            onAdd={onAdd}
          />
        ))}
      </div>
      <DragOverlay>{activeTicket ? <TicketCardBody ticket={activeTicket} floating /> : null}</DragOverlay>
    </DndContext>
  );
}

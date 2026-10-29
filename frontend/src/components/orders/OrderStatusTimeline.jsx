import React from "react";
import { formatDateTime, formatStatus } from "../../utils/format";

export default function OrderStatusTimeline({ events }) {
  if (!events.length) return <p className="muted">No status updates yet.</p>;
  return (
    <ol className="status-timeline">
      {events.map((event, index) => (
        <li key={`${event.status}-${index}`} className={index === events.length - 1 ? "is-latest" : ""}>
          <span className="timeline-dot" aria-hidden="true" />
          <span className="timeline-body">
            <strong>{formatStatus(event.status)}</strong>
            {event.note ? <span>{event.note}</span> : null}
            <time className="muted" dateTime={event.created_at}>{formatDateTime(event.created_at)}</time>
          </span>
        </li>
      ))}
    </ol>
  );
}

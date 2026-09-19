import type { Conversation } from "@/services/api/messaging";
import type { CareNotification, NotificationPage } from "@/services/api/notifications";

export function upsertConversation(current: Conversation[] | undefined, next: Conversation) {
  if (!current) return current;
  return [next, ...current.filter((item) => item.public_id !== next.public_id)]
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at));
}

export function upsertNotification(current: NotificationPage | undefined, next: CareNotification) {
  if (!current) return current;
  const existing = current.results.find((item) => item.public_id === next.public_id);
  const unreadDelta = existing ? Number(!next.read_at) - Number(!existing.read_at) : Number(!next.read_at);
  return {
    unread_count: Math.max(0, current.unread_count + unreadDelta),
    results: [next, ...current.results.filter((item) => item.public_id !== next.public_id)].slice(0, 100),
  };
}

export function markNotificationCachedRead(current: NotificationPage | undefined, next: CareNotification) {
  if (!current) return current;
  const previous = current.results.find((item) => item.public_id === next.public_id);
  if (!previous) return current;
  return {
    unread_count: Math.max(0, current.unread_count - Number(!previous.read_at && !!next.read_at)),
    results: current.results.map((item) => item.public_id === next.public_id ? next : item),
  };
}

export function markAllNotificationsCachedRead(current: NotificationPage | undefined) {
  if (!current) return current;
  const now = new Date().toISOString();
  return { unread_count: 0, results: current.results.map((item) => ({ ...item, read_at: item.read_at || now })) };
}

export function applyNotificationReads(
  current: NotificationPage | undefined,
  ids: string[],
  readAt: string,
  unreadCount: number,
) {
  if (!current) return current;
  const readIds = new Set(ids);
  return {
    unread_count: unreadCount,
    results: current.results.map((item) => readIds.has(item.public_id) && !item.read_at
      ? { ...item, read_at: readAt } : item),
  };
}

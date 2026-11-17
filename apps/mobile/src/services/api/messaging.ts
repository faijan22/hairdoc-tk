import { apiGet, apiPost, apiPostForm } from "./client";
import { API_BASE_URL, REALTIME_API_BASE_URL } from "./config";
import {
  conversationSchema,
  messagePageSchema,
  messageSchema,
  ticketSchema,
} from "./messageSchemas";
import { appendAssetToFormData, type MultipartAsset } from "./multipart";

export type { Conversation, Message } from "./messageSchemas";

export function parseRealtimeMessage(value: unknown) {
  return messageSchema.parse(value);
}

export function parseRealtimeConversation(value: unknown) {
  return conversationSchema.parse(value);
}

function apiPath(url: string) {
  const parsed = new URL(url);
  return `${parsed.pathname}${parsed.search}`.replace(/^\/api\/v1/, "");
}
export async function getConversations() {
  return conversationSchema
    .array()
    .parse(await apiGet<unknown>("/conversations/"));
}
export async function getConversation(id: string) {
  return conversationSchema.parse(
    await apiGet<unknown>(`/conversations/${id}/`),
  );
}
export async function getMessages(id: string, cursorUrl?: string) {
  return messagePageSchema.parse(
    await apiGet<unknown>(
      cursorUrl ? apiPath(cursorUrl) : `/conversations/${id}/messages/`,
    ),
  );
}
export type MessageImageAsset = MultipartAsset & {
  width?: number;
  height?: number;
};
export async function sendMessage(
  id: string,
  body: string,
  clientMessageId: string,
  image?: MessageImageAsset,
  replyToPublicId?: string,
) {
  if (!image)
    return messageSchema.parse(
      await apiPost<unknown>(`/conversations/${id}/messages/`, {
        body,
        client_message_id: clientMessageId,
        reply_to_public_id: replyToPublicId,
      }),
    );
  const form = new FormData();
  form.append("body", body);
  form.append("client_message_id", clientMessageId);
  if (replyToPublicId) form.append("reply_to_public_id", replyToPublicId);
  await appendAssetToFormData(form, "file", image, "message-image.jpg");
  return messageSchema.parse(
    await apiPostForm<unknown>(`/conversations/${id}/messages/`, form),
  );
}
export async function deleteMessage(id: string, messageId: string, mode: "self" | "everyone") {
  return apiPost<{ mode: "self" | "everyone"; message_public_id: string }>(
    `/conversations/${id}/messages/${messageId}/delete/`, { mode },
  );
}
export function privateMessageImageUrl(path: string) {
  const origin = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
  return `${origin}${path}`;
}
export async function markConversationRead(id: string, messageId?: string) {
  return apiPost<{ read_through: string | null }>(
    `/conversations/${id}/read/`,
    messageId ? { message_public_id: messageId } : {},
  );
}
export async function getRealtimeTicket(id: string) {
  return ticketSchema.parse(
    await apiPost<unknown>("/realtime/ticket/", { conversation_public_id: id }),
  );
}
export async function getInboxRealtimeTicket() {
  return ticketSchema.parse(await apiPost<unknown>("/realtime/ticket/", {}));
}
export function hasRealtimeTransport() {
  return !REALTIME_API_BASE_URL.includes("/__hairdoc_api/");
}
export function realtimeUrl(path: string, ticket: string): string | null {
  if (!hasRealtimeTransport()) return null;
  const url = new URL(REALTIME_API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = path;
  url.search = "";
  url.searchParams.set("ticket", ticket);
  return url.toString();
}

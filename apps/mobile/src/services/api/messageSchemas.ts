import { z } from "zod";

export const messageSchema = z.object({
  public_id: z.string().uuid(), conversation_public_id: z.string().uuid(), sender_public_id: z.string().uuid(),
  sender_name: z.string(), body: z.string(), status: z.enum(["SENT", "READ"]),
  attachment: z.object({
    public_id: z.string().uuid(), content_type: z.string(), byte_size: z.number(), width: z.number(), height: z.number(),
    content_path: z.string(),
  }).nullable(), client_message_id: z.string().uuid(), created_at: z.string(),
  deleted_for_everyone: z.boolean().default(false),
  reply_to: z.object({
    public_id: z.string().uuid(), sender_name: z.string(), body: z.string(),
    deleted_for_everyone: z.boolean(), has_attachment: z.boolean(),
  }).nullable().default(null),
});
export const conversationSchema = z.object({
  public_id: z.string().uuid(), consultation_public_id: z.string().uuid(), service_name: z.string(),
  status: z.enum(["ACTIVE", "CLOSED"]), other_member_name: z.string(), last_message: messageSchema.nullable(),
  unread_count: z.number().int().nonnegative(), created_at: z.string(), updated_at: z.string(),
});
export const messagePageSchema = z.object({ next: z.string().nullable(), previous: z.string().nullable(), results: z.array(messageSchema) });
export const ticketSchema = z.object({ ticket: z.string(), expires_at: z.string(), websocket_path: z.string() });
export type Conversation = z.infer<typeof conversationSchema>;
export type Message = z.infer<typeof messageSchema>;

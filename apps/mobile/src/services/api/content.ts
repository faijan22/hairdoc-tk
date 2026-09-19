import { z } from "zod";

export const contentItemSchema = z.object({
  public_id: z.string().uuid(),
  type: z.enum(["TEDX", "BOOK", "PRODUCT", "RESOURCE", "ARTICLE", "PROMOTION"]),
  title: z.string(),
  slug: z.string(),
  summary: z.string(),
  external_url: z.string(),
  published_at: z.string().nullable(),
});

export type ContentItem = z.infer<typeof contentItemSchema>;

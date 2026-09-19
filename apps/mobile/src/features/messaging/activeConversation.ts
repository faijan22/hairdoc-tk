let activeConversationId: string | null = null;

export function setActiveConversation(id: string | null) {
  activeConversationId = id;
}

export function isActiveConversationRoute(route: unknown) {
  return (
    typeof route === "string" &&
    activeConversationId !== null &&
    route === `/messages/${activeConversationId}`
  );
}

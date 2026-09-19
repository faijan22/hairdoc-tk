# Current Task - 13K Chat Interaction and Message Controls

**Status:** `IN PROGRESS` — implementation/tests pass; physical two-device verification is still required.  
**Started:** 2026-09-18  
**Next planned, not started:** Task 13L - configure and verify TK's Square sandbox credentials; then Task 14 hardening.

## Scope

- Show text/image sends immediately, expose two-way typing clearly, and support reply, delete for me, and delete for everyone in the private client↔TK chat.

## Completed

- Send no longer awaits query cancellation. Text/image bubbles appear at tap time with a clock, survive background refetch, and reconcile by idempotent client UUID; a failed bubble can be retried.
- Backend-authenticated typing appears as visible text and animated dots by the composer and in the conversation header. Reconnecting with a draft re-announces typing; no polling is presented as live.
- A missed heartbeat closes and reconnects a stale socket. Chat history loads once, automatically fetches older cursor pages on scroll, and catches up on reconnect; no timed message or inbox polling.
- One user-scoped WebSocket keeps the inbox and in-app notifications current even outside a conversation; the open conversation has its own WebSocket regardless of peer presence. Foreground remote banners are suppressed in favor of the in-app banner. App foregrounding revalidates inbox/notifications.
- Socket events now carry per-member inbox snapshots and user-scoped notification data. The UI updates its cache directly; send, receive, typing, read, and active-chat notification events no longer trigger repeated list/detail GETs. Initial load, cursor history, missing-cache fallback, and reconnect/foreground catch-up still use REST. Chat cache keys include the signed-in user.
- Opening a chat seeds its detail from the inbox row when available; active-chat notification reads reuse the conversation read acknowledgement instead of a second POST. The notification row is committed before the message socket event to avoid a read-before-notification race.
- Typing presence refreshes on the socket while input continues, stops after three seconds idle or composer blur, and the receiver has a five-second expiry; no HTTP calls are made for typing.
- The local launcher explicitly embeds the current LAN realtime endpoint separately from the Expo REST tunnel bridge. Native socket access still needs physical-device acceptance.
- Native clients without a browser Origin header can connect using the one-use ticket; browser connections retain host-origin validation.
- Replies store a same-conversation message reference and show a short quote. Both members may hide a message for themselves; only the sender may delete for everyone. Shared deletion retains a tombstone, strips body, removes the private attachment and signed access, and broadcasts the change.
- Added and applied migrations `messaging.0004` and `0005`; focused inbox/conversation socket, authorization, reply, image-removal, and frontend cache tests pass. Full suite: 64 backend and 24 mobile tests; lint/typecheck clean.
- Square credentials were not changed or stored; sandbox configuration/verification is the next separately approved slice.

## Remaining acceptance check

- Restart `npm run dev` so Django and Expo load these changes. Open the same conversation on client and TK devices; both headers must say `Live`. Type continuously for 10+ seconds and confirm presence stays visible; send text/image and confirm tap-time clock, prompt peer arrival, then one/two ticks. Leave one account in the inbox and verify immediate row/unread/banner updates and tapping the banner opens the chat. During ordinary text sends, the browser network panel should show no repeated conversation/detail/notification GETs; initial load, missed-event catch-up, and image-token fetches may still use REST. Verify cursor history, reply and both deletion modes. If either header stays `Reconnecting…`, inspect the direct device-to-LAN WebSocket transport before marking done. Remote background push requires a signed development/store build and credentials; Expo Go cannot validate it.

## Stop boundary

Do not start Square credential activation or Task 14 without approval.
